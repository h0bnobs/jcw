import os
import sqlite3
from sqlite3 import Connection
from typing import Optional, List, Dict, Any


def initialise_database() -> Connection:
    if "torrents.db" in os.listdir(os.getcwd()):
        return sqlite3.connect("torrents.db")
    else:
        con = sqlite3.connect("torrents.db")
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


def add_torrent(con: Connection, name: str, magnet: str, size: Optional[str]) -> None:
    con.execute("INSERT INTO torrents (name, magnet, size, status) VALUES (?, ?, ?, 'queued')", (name, magnet, size))
    con.commit()


def get_current_download(con: Connection) -> Optional[Dict[str, Any]]:
    cur = con.cursor()
    cur.execute("SELECT * FROM torrents WHERE status = 'downloading' LIMIT 1")
    row = cur.fetchone()
    return dict_from_row(cur, row)


def get_next_in_queue(con: Connection) -> Optional[Dict[str, Any]]:
    cur = con.cursor()
    cur.execute("SELECT * FROM torrents WHERE status = 'queued' ORDER BY added_at ASC LIMIT 1")
    row = cur.fetchone()
    return dict_from_row(cur, row)


def get_last_completed(con: Connection) -> Optional[Dict[str, Any]]:
    cur = con.cursor()
    cur.execute("SELECT * FROM torrents WHERE status = 'completed' ORDER BY completed_at DESC LIMIT 1")
    row = cur.fetchone()
    return dict_from_row(cur, row)


def get_time_started(con: Connection) -> Optional[str]:
    cur = con.cursor()
    cur.execute("SELECT started_at FROM torrents WHERE status = 'downloading' LIMIT 1")
    result = cur.fetchone()
    return result[0] if result else None


def update_progress(con: Connection, torrent_id: int, progress: int) -> None:
    con.execute("UPDATE torrents SET progress = ? WHERE id = ?", (progress, torrent_id))
    con.commit()


def mark_as_downloading(con: Connection, torrent_id: int) -> None:
    con.execute("UPDATE torrents SET status = 'downloading', started_at = CURRENT_TIMESTAMP WHERE id = ?", (torrent_id,))
    con.commit()


def mark_as_completed(con: Connection, torrent_id: int) -> None:
    con.execute("UPDATE torrents SET status = 'completed', completed_at = CURRENT_TIMESTAMP, progress = 100 WHERE id = ?", (torrent_id,))
    con.commit()


def get_all_queued(con: Connection) -> List[Dict[str, Any]]:
    cur = con.cursor()
    cur.execute("SELECT * FROM torrents WHERE status = 'queued' ORDER BY added_at ASC")
    return [dict_from_row(cur, row) for row in cur.fetchall()]


def get_all_completed(con, limit: int = 10) -> List[Dict[str, Any]]:
    cur = con.cursor()
    cur.execute("""
        SELECT * FROM torrents
        WHERE status = 'completed'
        ORDER BY completed_at DESC, id DESC
        LIMIT ?
    """, (limit,))
    return [dict_from_row(cur, row) for row in cur.fetchall()]



def get_all(con: Connection) -> List[Dict[str, Any]]:
    cur = con.cursor()
    cur.execute("SELECT * FROM torrents ORDER BY added_at DESC")
    return [dict_from_row(cur, row) for row in cur.fetchall()]


def dict_from_row(cur, row) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {description[0]: value for description, value in zip(cur.description, row)}
