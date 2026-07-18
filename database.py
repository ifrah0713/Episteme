# ============================================================
# Episteme — Database (database.py)
# Purpose: Save chat history per user using SQLite
# ============================================================

import sqlite3
from datetime import datetime

# ─── Constants ────────────────────────────────────────────────
DB_PATH = "./episteme.db"


# ─── Initialize Database ──────────────────────────────────────
def init_db():
    """Create tables if they don't exist."""
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT    NOT NULL,
            user_email TEXT    NOT NULL DEFAULT '',
            created_at TEXT    NOT NULL,
            updated_at TEXT    NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id    INTEGER NOT NULL,
            role       TEXT    NOT NULL,
            content    TEXT    NOT NULL,
            created_at TEXT    NOT NULL,
            FOREIGN KEY (chat_id) REFERENCES chats(id)
        )
    """)

    # Add user_email column if it doesn't exist (migration)
    try:
        cursor.execute("ALTER TABLE chats ADD COLUMN user_email TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass  # Column already exists

    conn.commit()
    conn.close()


# ─── Create New Chat ──────────────────────────────────────────
def create_chat(title: str = "New Chat", user_email: str = "") -> int:
    """Create a new chat and return its ID."""
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now    = datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO chats (title, user_email, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (title, user_email, now, now)
    )
    chat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return chat_id


# ─── Save Message ─────────────────────────────────────────────
def save_message(chat_id: int, role: str, content: str):
    """Save a message to the database."""
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now    = datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO messages (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (chat_id, role, content, now)
    )

    # Update chat title from first user message
    if role == "user":
        cursor.execute(
            "SELECT COUNT(*) FROM messages WHERE chat_id = ? AND role = 'user'",
            (chat_id,)
        )
        count = cursor.fetchone()[0]
        if count == 1:
            title = content[:40] + "..." if len(content) > 40 else content
            cursor.execute(
                "UPDATE chats SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, chat_id)
            )
        else:
            cursor.execute(
                "UPDATE chats SET updated_at = ? WHERE id = ?",
                (now, chat_id)
            )

    conn.commit()
    conn.close()


# ─── Load Messages ────────────────────────────────────────────
def load_messages(chat_id: int) -> list:
    """Load all messages for a chat."""
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id",
        (chat_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    return [{"role": row[0], "content": row[1]} for row in rows]


# ─── Get All Chats for User ───────────────────────────────────
def get_all_chats(user_email: str = "") -> list:
    """Get all chats for a specific user ordered by most recent."""
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if user_email:
        cursor.execute(
            "SELECT id, title, updated_at FROM chats WHERE user_email = ? ORDER BY updated_at DESC",
            (user_email,)
        )
    else:
        cursor.execute(
            "SELECT id, title, updated_at FROM chats ORDER BY updated_at DESC"
        )

    rows = cursor.fetchall()
    conn.close()

    return [{"id": row[0], "title": row[1], "updated_at": row[2]} for row in rows]


# ─── Delete Chat ──────────────────────────────────────────────
def delete_chat(chat_id: int):
    """Delete a chat and all its messages."""
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    cursor.execute("DELETE FROM chats WHERE id = ?", (chat_id,))

    conn.commit()
    conn.close()


# ─── Save User ────────────────────────────────────────────────
def save_user(name: str):
    """Legacy function — kept for compatibility."""
    pass


# ─── Get User ─────────────────────────────────────────────────
def get_user() -> str:
    """Legacy function — kept for compatibility."""
    return ""


# ─── Initialize on Import ─────────────────────────────────────
init_db()