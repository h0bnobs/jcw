import os

from flask import app


def is_video_file(filename: str) -> bool:
    """
    Check if the file has a video extension.
    :param filename: Name of the file.
    :return: True if the file is a video file, False otherwise.
    """
    video_extensions = {"mp4", "mkv", "avi", "mov", "wmv", "flv"}
    return filename.lower().rsplit(".", 1)[-1] in video_extensions

def is_folder(path: str) -> bool:
    """
    Check if the given path is a folder.
    :param path: Path to check.
    :return: True if the path is a folder, False otherwise.
    """
    return os.path.isdir(path)

def get_all_completed_downloads(download_dir: str = None) -> list:
    """
    Retrieve all completed downloads from the download directory.
    :return: List of completed downloads with relevant details.
    """
    if download_dir:
        downloads = []
        for root, dirs, files in os.walk(download_dir):
            downloads.extend([file for file in files if is_video_file(file)])
        return downloads
    return []
