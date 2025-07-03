import sqlite3
import time

import pytest

from src.db.init_db import (
    add_torrent,
    get_all_queued,
    get_next_in_queue,
    mark_as_downloading,
    get_current_download,
    get_time_started,
    update_progress,
    mark_as_completed,
    get_last_completed,
    get_all_completed,
)


@pytest.fixture
def in_memory_db():
    con = sqlite3.connect(":memory:")
    con.execute("""
        CREATE TABLE torrents (
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
    yield con
    con.close()


def test_add_and_get_queued(in_memory_db):
    add_torrent(in_memory_db, "Ubuntu", "magnet:?xt=ubuntu", "1 GB")
    add_torrent(in_memory_db, "Kali", "magnet:?xt=kali", "2 GB")
    queued = get_all_queued(in_memory_db)
    assert len(queued) == 2
    assert queued[0]["name"] == "Ubuntu"
    assert queued[1]["magnet"] == "magnet:?xt=kali"


def test_get_next_and_mark_downloading(in_memory_db):
    add_torrent(in_memory_db, "Arch", "magnet:?xt=arch", "1.5 GB")
    torrent = get_next_in_queue(in_memory_db)
    mark_as_downloading(in_memory_db, torrent["id"])
    current = get_current_download(in_memory_db)
    assert current["name"] == "Arch"
    assert get_time_started(in_memory_db) is not None


def test_update_progress(in_memory_db):
    add_torrent(in_memory_db, "Fedora", "magnet:?xt=fedora", "2 GB")
    torrent = get_next_in_queue(in_memory_db)
    mark_as_downloading(in_memory_db, torrent["id"])
    update_progress(in_memory_db, torrent["id"], 47)
    current = get_current_download(in_memory_db)
    assert current["progress"] == 47


def test_complete_download(in_memory_db):
    add_torrent(in_memory_db, "Debian", "magnet:?xt=debian", "3 GB")
    torrent = get_next_in_queue(in_memory_db)
    mark_as_downloading(in_memory_db, torrent["id"])
    mark_as_completed(in_memory_db, torrent["id"])
    assert get_current_download(in_memory_db) is None
    completed = get_last_completed(in_memory_db)
    assert completed["name"] == "Debian"
    assert completed["progress"] == 100


def test_get_all_completed_limit(in_memory_db):
    for i in range(5):
        add_torrent(in_memory_db, f"Movie {i}", f"magnet:?xt={i}", f"{i+1} GB")
        t = get_next_in_queue(in_memory_db)
        mark_as_downloading(in_memory_db, t["id"])
        time.sleep(0.1)
        mark_as_completed(in_memory_db, t["id"])

    recent = get_all_completed(in_memory_db, limit=3)
    assert len(recent) == 3
    assert recent[0]["name"] == "Movie 4"
    assert recent[2]["name"] == "Movie 2"
