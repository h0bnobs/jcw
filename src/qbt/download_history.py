from flask import session
import os

def get_all_completed_downloads() -> list:
    """
    Retrieve all completed downloads from the download directory.
    :return: List of completed downloads with relevant details.
    """
    download_directory = session["download_dir"]
    downloads = os.listdir(download_directory)
    return downloads