import unittest
from unittest.mock import Mock, patch

from src.qbt.remove_torrents import remove_completed_torrents
from src.qbt.tv_organizer import NOT_TV, ORGANIZED, REVIEW, OrganizationResult


class RemoveCompletedTorrentsTests(unittest.TestCase):
    def setUp(self):
        self.torrent = {
            "hash": "a" * 40,
            "name": "Example.Show.S01E02",
            "state": "pausedUP",
            "progress": 1.0,
        }
        self.client = Mock()
        self.client.torrents.return_value = [self.torrent]

    @patch("src.qbt.remove_torrents.qb")
    @patch("src.qbt.remove_torrents.organize_completed_torrent")
    def test_review_torrent_is_not_removed(self, organize, get_client):
        get_client.return_value = self.client
        organize.return_value = OrganizationResult(REVIEW, "ambiguous show")

        remove_completed_torrents("/downloads", "/shows")

        organize.assert_called_once_with(self.torrent, "/downloads", "/shows")
        self.client.delete.assert_not_called()

    @patch("src.qbt.remove_torrents.qb")
    @patch("src.qbt.remove_torrents.organize_completed_torrent")
    def test_successfully_organized_torrent_is_removed(self, organize, get_client):
        get_client.return_value = self.client
        organize.return_value = OrganizationResult(ORGANIZED, "filed 1 episode video")

        remove_completed_torrents("/downloads", "/shows")

        self.client.delete.assert_called_once_with(self.torrent["hash"])

    @patch("src.qbt.remove_torrents.qb")
    @patch("src.qbt.remove_torrents.organize_completed_torrent")
    def test_non_tv_cleanup_behavior_is_preserved(self, organize, get_client):
        get_client.return_value = self.client
        organize.return_value = OrganizationResult(NOT_TV)

        remove_completed_torrents("/downloads", "/shows")

        self.client.delete.assert_called_once_with(self.torrent["hash"])

    @patch("src.qbt.remove_torrents.qb")
    @patch("src.qbt.remove_torrents.organize_completed_torrent", side_effect=OSError("disk error"))
    def test_organizer_error_fails_closed(self, organize, get_client):
        get_client.return_value = self.client

        remove_completed_torrents("/downloads", "/shows")

        self.client.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
