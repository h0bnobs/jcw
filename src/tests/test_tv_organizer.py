import os
import tempfile
import unittest

from src.qbt.tv_organizer import (
    ORGANIZED,
    REVIEW,
    match_library_show,
    organize_completed_torrent,
    parse_episode_release,
    release_is_in_library,
)


class TvOrganizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = self.temp.name
        self.download_dir = os.path.join(self.root, "downloads")
        self.shows_dir = os.path.join(self.root, "shows")
        os.makedirs(self.download_dir)
        os.makedirs(self.shows_dir)
        self.show_path = os.path.join(self.shows_dir, "Example Show (2019) [tmdbid-123]")
        os.makedirs(self.show_path)

    def tearDown(self):
        self.temp.cleanup()

    def _torrent(self, release_name="Example.Show.2019.S01E02.1080p.WEB-DL"):
        filename = release_name + ".mkv"
        source = os.path.join(self.download_dir, filename)
        with open(source, "wb") as video:
            video.write(b"episode data")
        return {
            "name": release_name,
            "save_path": self.download_dir,
            "content_path": source,
        }, source, filename

    def test_parse_sxxexx_and_multi_episode_release(self):
        release = parse_episode_release("Example.Show.2019.S01E02-E04.1080p.mkv")
        self.assertEqual(release.series_title, "Example Show")
        self.assertEqual(release.year, "2019")
        self.assertEqual(release.season, 1)
        self.assertEqual(release.episodes, (2, 3, 4))

        alternate = parse_episode_release("Example Show 2x07.mkv")
        self.assertEqual(alternate.episodes, (7,))
        self.assertIsNone(parse_episode_release("Movie.2024.1920x1080.mkv"))

    def test_matches_existing_library_folder_without_tmdb_access(self):
        show, reason = match_library_show("Example Show", self.shows_dir)
        self.assertEqual(reason, "")
        self.assertEqual(show.tmdb_id, "123")

    def test_files_episode_to_existing_season_folder(self):
        torrent, source, filename = self._torrent()

        result = organize_completed_torrent(torrent, self.download_dir, self.shows_dir)

        destination = os.path.join(self.show_path, "Season 01", filename)
        self.assertEqual(result.status, ORGANIZED)
        self.assertFalse(os.path.exists(source))
        self.assertTrue(os.path.isfile(destination))
        self.assertTrue(release_is_in_library(torrent["name"], self.shows_dir))

    def test_unknown_show_is_left_untouched_for_review(self):
        torrent, source, _filename = self._torrent("New.Show.S01E02.1080p")

        result = organize_completed_torrent(torrent, self.download_dir, self.shows_dir)

        self.assertEqual(result.status, REVIEW)
        self.assertTrue(os.path.isfile(source))

    def test_existing_destination_is_never_overwritten(self):
        torrent, source, filename = self._torrent()
        season_dir = os.path.join(self.show_path, "Season 01")
        os.makedirs(season_dir)
        destination = os.path.join(season_dir, filename)
        with open(destination, "wb") as existing:
            existing.write(b"keep existing")

        result = organize_completed_torrent(torrent, self.download_dir, self.shows_dir)

        self.assertEqual(result.status, REVIEW)
        self.assertTrue(os.path.isfile(source))
        with open(destination, "rb") as existing:
            self.assertEqual(existing.read(), b"keep existing")

    def test_already_filed_episode_is_not_added_under_a_second_name(self):
        torrent, source, _filename = self._torrent()
        season_dir = os.path.join(self.show_path, "Season 01")
        os.makedirs(season_dir)
        existing = os.path.join(season_dir, "Example.Show.2019.S01E02.720p.mkv")
        with open(existing, "wb") as video:
            video.write(b"existing episode")

        result = organize_completed_torrent(torrent, self.download_dir, self.shows_dir)

        self.assertEqual(result.status, REVIEW)
        self.assertTrue(os.path.isfile(source))
        self.assertTrue(os.path.isfile(existing))

    def test_new_show_folder_is_created_when_resolver_identifies_it(self):
        from src.qbt.show_lookup import ShowIdentity

        torrent, source, filename = self._torrent("Brand.New.Show.S01E01.1080p.WEB-DL")

        def resolver(title, year):
            return ShowIdentity("Brand New Show", "2021", tmdb_id=None, imdb_id="tt9999999")

        result = organize_completed_torrent(
            torrent, self.download_dir, self.shows_dir, resolver,
        )

        destination = os.path.join(
            self.shows_dir, "Brand New Show (2021) [imdbid-tt9999999]", "Season 01", filename,
        )
        self.assertEqual(result.status, ORGANIZED)
        self.assertTrue(os.path.isfile(destination))
        self.assertFalse(os.path.exists(source))

    def test_resolver_tmdb_id_is_used_in_new_folder_name(self):
        from src.qbt.show_lookup import ShowIdentity

        torrent, _source, filename = self._torrent("Brand.New.Show.S02E03.1080p.WEB-DL")

        def resolver(title, year):
            return ShowIdentity("Brand New Show", "2021", tmdb_id="4242", imdb_id="tt9999999")

        result = organize_completed_torrent(
            torrent, self.download_dir, self.shows_dir, resolver,
        )

        destination = os.path.join(
            self.shows_dir, "Brand New Show (2021) [tmdbid-4242]", "Season 02", filename,
        )
        self.assertEqual(result.status, ORGANIZED)
        self.assertTrue(os.path.isfile(destination))

    def test_new_show_without_identity_is_left_for_review(self):
        torrent, source, _filename = self._torrent("Unknowable.Show.S01E02.1080p")

        result = organize_completed_torrent(
            torrent, self.download_dir, self.shows_dir, lambda title, year: None,
        )

        self.assertEqual(result.status, REVIEW)
        self.assertTrue(os.path.isfile(source))

    def test_retry_after_file_move_is_idempotent(self):
        torrent, _source, filename = self._torrent()
        first = organize_completed_torrent(torrent, self.download_dir, self.shows_dir)

        second = organize_completed_torrent(torrent, self.download_dir, self.shows_dir)

        self.assertEqual(first.status, ORGANIZED)
        self.assertEqual(second.status, ORGANIZED)
        self.assertTrue(os.path.isfile(os.path.join(self.show_path, "Season 01", filename)))


if __name__ == "__main__":
    unittest.main()
