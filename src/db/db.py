import os
import sqlite3
from sqlite3 import Connection
from typing import Optional, List, Dict, Any


def initialise_database() -> Connection:
    if "torrents.db" in os.listdir(os.getcwd()):
        return sqlite3.connect("torrents.db")
    else:
        con = sqlite3.connect("torrents.db", check_same_thread=False)
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS torrents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            magnet TEXT NOT NULL,
            size TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            progress INTEGER DEFAULT 0,
            status TEXT NOT NULL CHECK (
                status IN ('queued', 'downloading', 'completed')
            )
        );
        """)
        con.commit()
        return con

def get_connection() -> Connection:
    """
    Get a connection to the SQLite database.
    :return: SQLite connection object.
    """
    return sqlite3.connect("torrents.db", check_same_thread=False)

def add_torrent(con: Connection, name: str, magnet: str, size: Optional[str]) -> int:
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO torrents (name, magnet, size, status) VALUES (?, ?, ?, 'queued')",
        (name, magnet, size),
    )
    con.commit()
    return cur.lastrowid


def get_current_download(con: Connection) -> Optional[Dict[str, Any]]:
    """
    Retrieve the torrent currently being downloaded.
    :param con: SQLite database connection.
    :return: Dictionary with torrent details or None if none are downloading.
    """
    cur = con.cursor()
    cur.execute("SELECT * FROM torrents WHERE status = 'downloading' LIMIT 1")
    row = cur.fetchone()
    return dict_from_row(cur, row)


def get_next_in_queue(con: Connection) -> Optional[Dict[str, Any]]:
    """
    Get the next torrent in the queue (earliest added).
    :param con: SQLite database connection.
    :return: Dictionary with torrent details or None if queue is empty.
    """
    cur = con.cursor()
    cur.execute("SELECT * FROM torrents WHERE status = 'queued' ORDER BY added_at ASC LIMIT 1")
    row = cur.fetchone()
    return dict_from_row(cur, row)


def get_last_completed(con: Connection) -> Optional[Dict[str, Any]]:
    """
    Retrieve the most recently completed torrent.
    :param con: SQLite database connection.
    :return: Dictionary with torrent details or None if no completed torrents exist.
    """
    cur = con.cursor()
    cur.execute("SELECT * FROM torrents WHERE status = 'completed' ORDER BY completed_at DESC LIMIT 1")
    row = cur.fetchone()
    return dict_from_row(cur, row)


def get_time_started(con: Connection) -> Optional[str]:
    """
    Get the start time of the torrent currently being downloaded.
    :param con: SQLite database connection.
    :return: Timestamp as a string or None if no torrent is downloading.
    """
    cur = con.cursor()
    cur.execute("SELECT started_at FROM torrents WHERE status = 'downloading' LIMIT 1")
    result = cur.fetchone()
    return result[0] if result else None


def update_progress(con: Connection, torrent_id: int, progress: int) -> None:
    """
    Update the download progress of a torrent.
    :param con: SQLite database connection.
    :param torrent_id: ID of the torrent.
    :param progress: New progress value (0–100).
    """
    con.execute("UPDATE torrents SET progress = ? WHERE id = ?", (progress, torrent_id))
    con.commit()


def mark_as_downloading(con: Connection, torrent_id: int) -> None:
    """
    Mark a torrent as currently downloading and set the start time.
    :param con: SQLite database connection.
    :param torrent_id: ID of the torrent to mark as downloading.
    """
    con.execute("UPDATE torrents SET status = 'downloading', started_at = CURRENT_TIMESTAMP WHERE id = ?", (torrent_id,))
    con.commit()


def mark_as_completed(con: Connection, torrent_id: int) -> None:
    """
    Mark a torrent as completed and set the completion time and progress to 100%.
    :param con: SQLite database connection.
    :param torrent_id: ID of the torrent to mark as completed.
    """
    con.execute("UPDATE torrents SET status = 'completed', completed_at = CURRENT_TIMESTAMP, progress = 100 WHERE id = ?", (torrent_id,))
    con.commit()


def get_all_queued(con: Connection) -> List[Dict[str, Any]]:
    """
    Retrieve all torrents currently in the queue.
    :param con: SQLite database connection.
    :return: List of dictionaries, each representing a queued torrent.
    """
    cur = con.cursor()
    cur.execute("SELECT * FROM torrents WHERE status = 'queued' ORDER BY added_at ASC")
    return [dict_from_row(cur, row) for row in cur.fetchall()]


def get_all_completed(con, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve a list of recently completed torrents, ordered by completion time.
    :param con: SQLite database connection.
    :param limit: Maximum number of completed torrents to return.
    :return: List of dictionaries, each representing a completed torrent.
    """
    cur = con.cursor()
    cur.execute("""
        SELECT * FROM torrents
        WHERE status = 'completed'
        ORDER BY completed_at DESC, id DESC
        LIMIT ?
    """, (limit,))
    return [dict_from_row(cur, row) for row in cur.fetchall()]



def get_all(con: Connection) -> List[Dict[str, Any]]:
    """
    Retrieve all torrents in the database, ordered by time added (most recent first).
    :param con: SQLite database connection.
    :return: List of all torrent records as dictionaries.
    """
    cur = con.cursor()
    cur.execute("SELECT * FROM torrents ORDER BY added_at DESC")
    return [dict_from_row(cur, row) for row in cur.fetchall()]


def dict_from_row(cur, row) -> Optional[Dict[str, Any]]:
    """
    Convert a raw database row into a dictionary.
    :param cur: SQLite cursor with description of columns.
    :param row: Tuple containing row values.
    :return: Dictionary of column names to values, or None if row is None.
    """
    if row is None:
        return None
    return {description[0]: value for description, value in zip(cur.description, row)}
