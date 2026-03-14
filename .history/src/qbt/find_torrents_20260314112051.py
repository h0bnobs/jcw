import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
TIMEOUT = 15


def _get_torrents_tpb(search_string: str, page: int = 1) -> list:
    """Search The Pirate Bay for torrents."""
    try:
        url = f"https://thepiratebay10.org/search/{search_string}/{page}/99/0"
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(response.content, 'html.parser')

        table = soup.find('table', id='searchResult')
        if not table:
            return []

        torrents = []
        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) < 8:
                continue

            name_link = cols[1].find('a')
            if not name_link:
                continue
            name = name_link.text.strip()
            detail_href = name_link.get('href', '')
            detail_url = ('https://thepiratebay10.org' + detail_href) if detail_href and not detail_href.startswith('http') else detail_href

            magnet_a = cols[3].find('a', href=lambda h: h and h.startswith('magnet:'))
            if not magnet_a:
                continue

            seeders_text = cols[5].text.strip()
            leechers_text = cols[6].text.strip()

            torrents.append({
                'name': name,
                'size': cols[4].text.strip().replace('\xa0', ' '),
                'seeders': int(seeders_text) if seeders_text.isdigit() else 0,
                'leechers': int(leechers_text) if leechers_text.isdigit() else 0,
                'uploader': cols[7].text.strip(),
                'magnet': magnet_a['href'],
                'source': 'TPB',
                'detail_url': detail_url,
            })

        return torrents
    except Exception as e:
        print(f"TPB search failed: {e}")
        return []


def _fetch_magnet_1337x(url: str) -> str:
    """Fetch magnet link from a 1337x detail page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        magnet_a = soup.find('a', href=lambda h: h and h.startswith('magnet:'))
        return magnet_a['href'] if magnet_a else None
    except Exception:
        return None


def _get_torrents_1337x(search_string: str, page: int = 1) -> list:
    """Search 1337x for torrents."""
    try:
        url = f"https://1337x.to/search/{search_string}/{page}/"
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(response.content, 'html.parser')

        table = soup.find('table', class_='table-list')
        if not table or not table.find('tbody'):
            return []

        results = []
        for row in table.find('tbody').find_all('tr'):
            cols = row.find_all('td')
            if len(cols) < 6:
                continue

            links = cols[0].find_all('a')
            if len(links) < 2:
                continue

            name = links[1].text.strip()
            detail_url = 'https://1337x.to' + links[1]['href']

            seeders_text = cols[1].text.strip()
            leechers_text = cols[2].text.strip()

            # Size: remove hidden sorting spans
            for span in cols[4].find_all('span'):
                span.extract()
            size = cols[4].get_text(strip=True)

            results.append({
                'name': name,
                'size': size,
                'seeders': int(seeders_text) if seeders_text.isdigit() else 0,
                'leechers': int(leechers_text) if leechers_text.isdigit() else 0,
                'uploader': cols[5].text.strip(),
                'detail_url': detail_url,
                'source': '1337x',
            })

        # Fetch magnets from detail pages in parallel
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_map = {
                executor.submit(_fetch_magnet_1337x, r['detail_url']): i
                for i, r in enumerate(results)
            }
            for future in as_completed(future_map):
                idx = future_map[future]
                magnet = future.result()
                if magnet:
                    results[idx]['magnet'] = magnet

        return [r for r in results if 'magnet' in r]
    except Exception as e:
        print(f"1337x search failed: {e}")
        return []


def get_torrents(search_string: str, page: int = 1) -> list:
    """
    Search multiple torrent sites and return combined results sorted by seeders.
    """
    all_results = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(_get_torrents_tpb, search_string, page): 'tpb',
            executor.submit(_get_torrents_1337x, search_string, page): '1337x',
        }
        for future in as_completed(futures):
            try:
                all_results.extend(future.result())
            except Exception as e:
                print(f"Search error: {e}")

    all_results.sort(key=lambda x: x.get('seeders', 0), reverse=True)
    return all_results
