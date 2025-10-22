import os

from flask import session


def is_video_file(filename: str) -> bool:
    """
    Check if the file has a video extension.
    :param filename: Name of the file.
    :return: True if the file is a video file, False otherwise.
    """
    video_extensions = {"mp4", "mkv", "avi", "mov", "wmv", "flv"}
    return filename.lower().rsplit(".", 1)[-1] in video_extensions


def get_all_completed_downloads() -> list:
    """
    Retrieve all completed downloads from the download directory.
    :return: List of completed downloads with relevant details.
    """
    downloads = [file for file in os.listdir(session["download_dir"]) if is_video_file(file)]
    return downloads
