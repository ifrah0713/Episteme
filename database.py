# ============================================================
# Episteme — Database (database.py)
# Purpose: Save chat history per user using Supabase (PostgreSQL)
# Fallback: SQLite for local development
# ============================================================

import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─── Supabase Setup ───────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

supabase_client = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase connection failed, falling back to SQLite: {e}")

USE_SUPABASE = supabase_client is not None

# ─── SQLite Fallback ──────────────────────────────────────────
DB_PATH = "./episteme.db"


# ─── Initialize Database ──────────────────────────────────────
def init_db():
    if USE_SUPABASE:
        return

    conn = sqlite3.connect(DB_PATH)
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            email        TEXT    UNIQUE NOT NULL,
            display_name TEXT,
            created_at   TEXT    NOT NULL
        )
    """)

    try:
        cursor.execute("ALTER TABLE chats ADD COLUMN user_email TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass

    conn.commit()
    conn.close()


# ─── Create New Chat ──────────────────────────────────────────
def create_chat(title: str = "New Chat", user_email: str = "") -> int:
    now = datetime.now().isoformat()

    if USE_SUPABASE:
        try:
            result = supabase_client.table("chats").insert({
                "title": title,
                "user_email": user_email,
                "created_at": now,
                "updated_at": now
            }).execute()
            return result.data[0]["id"]
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
    now = datetime.now().isoformat()

    if USE_SUPABASE:
        try:
            supabase_client.table("messages").insert({
                "chat_id": chat_id,
                "role": role,
                "content": content,
                "created_at": now
            }).execute()

            if role == "user":
                result = supabase_client.table("messages").select("id", count="exact").eq("chat_id", chat_id).eq("role", "user").execute()
                count = result.count

                if count == 1:
                    title = content[:40] + "..." if len(content) > 40 else content
                    supabase_client.table("chats").update({
                        "title": title,
                        "updated_at": now
                    }).eq("id", chat_id).execute()
                else:
                    supabase_client.table("chats").update({
                        "updated_at": now
                    }).eq("id", chat_id).execute()
            return
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (chat_id, role, content, now)
    )
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
            cursor.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now, chat_id))
    conn.commit()
    conn.close()


# ─── Load Messages ────────────────────────────────────────────
def load_messages(chat_id: int) -> list:
    if USE_SUPABASE:
        try:
            result = supabase_client.table("messages").select("role, content").eq("chat_id", chat_id).order("id").execute()
            return [{"role": r["role"], "content": r["content"]} for r in result.data]
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
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
    if USE_SUPABASE:
        try:
            if user_email:
                result = supabase_client.table("chats").select("id, title, updated_at").eq("user_email", user_email).order("updated_at", desc=True).execute()
            else:
                result = supabase_client.table("chats").select("id, title, updated_at").order("updated_at", desc=True).execute()
            return result.data
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if user_email:
        cursor.execute(
            "SELECT id, title, updated_at FROM chats WHERE user_email = ? ORDER BY updated_at DESC",
            (user_email,)
        )
    else:
        cursor.execute("SELECT id, title, updated_at FROM chats ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "title": row[1], "updated_at": row[2]} for row in rows]


# ─── Delete Chat ──────────────────────────────────────────────
def delete_chat(chat_id: int):
    if USE_SUPABASE:
        try:
            supabase_client.table("messages").delete().eq("chat_id", chat_id).execute()
            supabase_client.table("chats").delete().eq("id", chat_id).execute()
            return
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    cursor.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()


# ─── User Display Name ────────────────────────────────────────
def get_display_name(email: str) -> str:
    if USE_SUPABASE:
        try:
            result = supabase_client.table("users").select("display_name").eq("email", email).execute()
            if result.data:
                return result.data[0]["display_name"] or ""
        except Exception as e:
            print(f"Supabase error: {e}")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT display_name FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row and row[0] else ""
    except Exception:
        return ""


def save_display_name(email: str, name: str):
    now = datetime.now().isoformat()

    if USE_SUPABASE:
        try:
            existing = supabase_client.table("users").select("id").eq("email", email).execute()
            if existing.data:
                supabase_client.table("users").update({"display_name": name}).eq("email", email).execute()
            else:
                supabase_client.table("users").insert({
                    "email": email,
                    "display_name": name,
                    "created_at": now
                }).execute()
            return
        except Exception as e:
            print(f"Supabase error: {e}")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, display_name, created_at) VALUES (?, ?, ?) ON CONFLICT(email) DO UPDATE SET display_name = ?",
            (email, name, now, name)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite error: {e}")


# ─── Legacy ───────────────────────────────────────────────────
def save_user(name: str):
    pass

def get_user() -> str:
    return ""


# ─── Initialize on Import ─────────────────────────────────────
init_db()
