from flask import session
import os

def get_all_completed_downloads() -> list:
    """
    Retrieve all completed downloads from the download directory.
    :return: List of completed downloads with relevant details.
    """
    downloads = [file for file in os.listdir(session["download_dir"]) if file.split(".")[-1].lower() in ["mp4", "mkv", "avi", "mov", "wmv", "flv"]]
    return downloads