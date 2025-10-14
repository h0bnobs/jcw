import unittest

import requests


class MyTestCase(unittest.TestCase):
    def test_piratebay_resolve(self):
        search_url = f"https://thepiratebay10.org/search/cars/1/99/0"
        response = requests.get(search_url)
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
