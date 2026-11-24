import unittest
from unittest.mock import patch

from src.qbt.show_lookup import ShowIdentity, resolve_show


class ShowIdentityTests(unittest.TestCase):
    def test_tmdb_tag_is_preferred_over_imdb(self):
        identity = ShowIdentity("Grey's Anatomy", "2005", tmdb_id="1416", imdb_id="tt0413573")
        self.assertEqual(identity.provider_tag(), "tmdbid-1416")
        self.assertEqual(identity.folder_name(), "Grey's Anatomy (2005) [tmdbid-1416]")

    def test_imdb_tag_used_when_no_tmdb_id(self):
        identity = ShowIdentity("Grey's Anatomy", "2005", tmdb_id=None, imdb_id="tt0413573")
        self.assertEqual(identity.folder_name(), "Grey's Anatomy (2005) [imdbid-tt0413573]")

    def test_path_separator_is_stripped_from_folder_name(self):
        identity = ShowIdentity("Face/Off", "1997", tmdb_id="123")
        self.assertNotIn("/", identity.folder_name())


class ResolveShowTests(unittest.TestCase):
    @patch("src.qbt.show_lookup.catalogue")
    def test_keyless_resolution_matches_despite_apostrophe(self, mock_catalogue):
        mock_catalogue.return_value = [
            {"id": "tt0413573", "name": "Grey's Anatomy", "year": "2005"},
        ]
        identity = resolve_show("Greys Anatomy", None, None)
        self.assertIsNotNone(identity)
        self.assertEqual(identity.imdb_id, "tt0413573")
        self.assertIsNone(identity.tmdb_id)
        self.assertEqual(identity.year, "2005")

    @patch("src.qbt.show_lookup._tmdb_id_for_imdb", return_value="1416")
    @patch("src.qbt.show_lookup.catalogue")
    def test_tmdb_key_upgrades_tag(self, mock_catalogue, _mock_find):
        mock_catalogue.return_value = [
            {"id": "tt0413573", "name": "Grey's Anatomy", "year": "2005-"},
        ]
        identity = resolve_show("Grey's Anatomy", "2005", "APIKEY")
        self.assertEqual(identity.tmdb_id, "1416")
        self.assertEqual(identity.folder_name(), "Grey's Anatomy (2005) [tmdbid-1416]")

    @patch("src.qbt.show_lookup.catalogue")
    def test_no_exact_title_match_returns_none(self, mock_catalogue):
        mock_catalogue.return_value = [
            {"id": "tt1", "name": "Completely Different Show", "year": "2000"},
        ]
        self.assertIsNone(resolve_show("Grey's Anatomy", None, None))

    @patch("src.qbt.show_lookup.catalogue")
    def test_ambiguous_match_without_year_returns_none(self, mock_catalogue):
        mock_catalogue.return_value = [
            {"id": "tt1", "name": "The Office", "year": "2005-2013"},
            {"id": "tt2", "name": "The Office", "year": "2001-2003"},
        ]
        self.assertIsNone(resolve_show("The Office", None, None))

    @patch("src.qbt.show_lookup.catalogue")
    def test_year_disambiguates_between_same_name_shows(self, mock_catalogue):
        mock_catalogue.return_value = [
            {"id": "tt_us", "name": "The Office", "year": "2005-2013"},
            {"id": "tt_uk", "name": "The Office", "year": "2001-2003"},
        ]
        identity = resolve_show("The Office", "2005", None)
        self.assertIsNotNone(identity)
        self.assertEqual(identity.imdb_id, "tt_us")

    @patch("src.qbt.show_lookup.catalogue")
    def test_release_year_with_no_matching_candidate_returns_none(self, mock_catalogue):
        mock_catalogue.return_value = [
            {"id": "tt1", "name": "The Office", "year": "2005-2013"},
        ]
        self.assertIsNone(resolve_show("The Office", "1999", None))

    @patch("src.qbt.show_lookup.catalogue", side_effect=RuntimeError("network down"))
    def test_lookup_failure_returns_none(self, _mock_catalogue):
        self.assertIsNone(resolve_show("Anything", None, None))


if __name__ == "__main__":
    unittest.main()
