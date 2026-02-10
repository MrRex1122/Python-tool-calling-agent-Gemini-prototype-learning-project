from __future__ import annotations

"""Mailbox viewer for SQLite-backed traces.

Usage:
    python scripts/mailbox_view.py --list
    python scripts/mailbox_view.py --thread-id <id>
"""

import argparse
import json
import os
import sqlite3
from pathlib import Path


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def list_threads(conn: sqlite3.Connection, limit: int) -> None:
    rows = conn.execute(
        """
        SELECT thread_id,
               COUNT(*) AS message_count,
               MIN(timestamp) AS first_ts,
               MAX(timestamp) AS last_ts
        FROM mailbox_messages
        GROUP BY thread_id
        ORDER BY last_ts DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    if not rows:
        print("No mailbox threads found.")
        return

    print("Threads:")
    for row in rows:
        print(
            f"- {row['thread_id']} | messages={row['message_count']} "
            f"| first={row['first_ts']} | last={row['last_ts']}"
        )


def show_thread(conn: sqlite3.Connection, thread_id: str) -> None:
    rows = conn.execute(
        """
        SELECT sender, recipient, content, timestamp
        FROM mailbox_messages
        WHERE thread_id = ?
        ORDER BY id ASC
        """,
        (thread_id,),
    ).fetchall()

    if not rows:
        print(f"No messages found for thread_id={thread_id}")
        return

    print(f"Thread {thread_id}:")
    for row in rows:
        try:
            content = json.loads(row["content"])
            content_text = json.dumps(content, ensure_ascii=False)
        except json.JSONDecodeError:
            content_text = row["content"]

        print(f"[{row['timestamp']}] {row['sender']} -> {row['recipient']}")
        print(f"  {content_text}")


def main() -> None:
    parser = argparse.ArgumentParser(description="View mailbox messages from SQLite.")
    parser.add_argument("--db", help="Path to mailbox SQLite file")
    parser.add_argument("--thread-id", help="Thread id to display")
    parser.add_argument("--list", action="store_true", help="List recent threads")
    parser.add_argument("--limit", type=int, default=10, help="Number of threads to list")
    args = parser.parse_args()

    db_path = args.db or os.getenv("MAILBOX_FILE", "data/mailbox.db")
    db_file = Path(db_path)
    if not db_file.exists():
        print(f"Mailbox DB not found: {db_file}")
        return

    with _connect(str(db_file)) as conn:
        if args.list or not args.thread_id:
            list_threads(conn, args.limit)
            if args.thread_id is None:
                return
        show_thread(conn, args.thread_id)


if __name__ == "__main__":
    main()
