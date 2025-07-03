import os
import sqlite3
from sqlite3 import Connection


def initialise_database() -> Connection:
    """
    Initialise the SQLite database for torrent management.
    :return: sqlite3.Connection object
    """
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
            progress INTEGER DEFAULT 0,          -- 0–100 percent
            status TEXT NOT NULL CHECK (
                status IN ('queued', 'downloading', 'completed')
            )
        );
        """)
        con.commit()
        return con
