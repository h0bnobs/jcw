import requests
from bs4 import BeautifulSoup
import webbrowser

def get_magnet_links(soup) -> list:
    magnets = []
    table = soup.find('table', id='searchResult')
    if not table:
        print("No search results found.")
        return []

    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 4:
            continue  # skip rows without enough columns

        fourth_td = cols[3]
        magnet_link = fourth_td.find('a', href=lambda href: href and href.startswith('magnet:'))
        if magnet_link:
            magnets.append(magnet_link['href'])
    return magnets

def get_torrent_names(soup) -> list:
    names = []
    table = soup.find('table', id='searchResult')
    if not table:
        print("No search results found.")
        return []

    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 4:
            continue

        second_td = cols[1]
        torrent_name = second_td.find('a').text.strip() if second_td.find('a') else None
        if torrent_name:
            names.append(torrent_name)
    return names

def get_num_of_seeders(soup) -> list:
    seeders = []
    table = soup.find('table', id='searchResult')
    if not table:
        print("No search results found.")
        return []

    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 4:
            continue

        sixth_td = cols[5]
        seeder_count = sixth_td.text.strip()
        if seeder_count.isdigit():
            seeders.append(int(seeder_count))
    return seeders

def get_num_of_leechers(soup) -> list:
    leechers = []
    table = soup.find('table', id='searchResult')
    if not table:
        print("No search results found.")
        return []

    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 4:
            continue

        seventh_td = cols[6]
        leecher_count = seventh_td.text.strip()
        if leecher_count.isdigit():
            leechers.append(int(leecher_count))
    return leechers

def get_size_of_torrent(soup) -> list:
    sizes = []
    table = soup.find('table', id='searchResult')
    if not table:
        print("No search results found.")
        return []

    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 4:
            continue

        fifth_td = cols[4]
        size = fifth_td.text.strip().replace('\xa0', ' ')
        if size:
            sizes.append(size)
    return sizes

def get_torrent_uploader(soup) -> list:
    sizes = []
    table = soup.find('table', id='searchResult')
    if not table:
        print("No search results found.")
        return []

    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 4:
            continue

        eighth_td = cols[7]
        size = eighth_td.text.strip()
        if size:
            sizes.append(size)
    return sizes

#num of seeders, torrent leachers, torrent size and uploader are?
def get_torrents(search_string: str) -> list:
    """
    Search The Pirate Bay for torrents matching the search string.
    :param search_string: Simple show/film to search for.
    :return: A list of dictionaries containing torrent details.
    """
    search_url = f"https://thepiratebay10.org/search/{search_string}/1/99/0"
    response = requests.get(search_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    magnets = get_magnet_links(soup)
    names = get_torrent_names(soup)
    sizes = get_size_of_torrent(soup)
    seeders = get_num_of_seeders(soup)
    leechers = get_num_of_leechers(soup)
    uploaders = get_torrent_uploader(soup)

    torrents = []
    for name, size, seeder, leecher, uploader, magnet in zip(
            names, sizes, seeders, leechers, uploaders, magnets
    ):
        torrents.append({
            "name": name,
            "size": size,
            "seeders": seeder,
            "leechers": leecher,
            "uploader": uploader,
            "magnet": magnet
        })

    return torrents
