import os
import sqlite3
import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# ── Supabase client ───────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")

supabase: Client = None
USE_SUPABASE = False

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        USE_SUPABASE = True
        print("✅ Supabase connected")
    except Exception as e:
        print(f"Supabase error: {e}")
        USE_SUPABASE = False

# ── SQLite fallback ───────────────────────────────────────────
DB_PATH = "episteme.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            user_email TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            display_name TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ── Chat functions ────────────────────────────────────────────
def create_chat(title: str, user_email: str = "") -> int:
    now = datetime.now().isoformat()
    if USE_SUPABASE:
        try:
            res = supabase.table("chats").insert({
                "title": title,
                "user_email": user_email,
                "created_at": now,
                "updated_at": now,
            }).execute()
            return res.data[0]["id"]
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO chats (title, user_email, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (title, user_email, now, now)
    )
    conn.commit()
    chat_id = c.lastrowid
    conn.close()
    return chat_id


def save_message(chat_id: int, role: str, content: str):
    now = datetime.now().isoformat()
    if USE_SUPABASE:
        try:
            supabase.table("messages").insert({
                "chat_id": chat_id,
                "role": role,
                "content": content,
                "created_at": now,
            }).execute()

            supabase.table("chats").update({"updated_at": now}).eq("id", chat_id).execute()
            return
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (chat_id, role, content, now)
    )
    c.execute("UPDATE chats SET updated_at=? WHERE id=?", (now, chat_id))
    conn.commit()
    conn.close()


def load_messages(chat_id: int) -> list:
    if USE_SUPABASE:
        try:
            res = supabase.table("messages").select("*").eq("chat_id", chat_id).order("created_at").execute()
            return [{"role": m["role"], "content": m["content"]} for m in res.data]
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE chat_id=? ORDER BY created_at", (chat_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]


def get_all_chats(user_email: str = "") -> list:
    if USE_SUPABASE:
        try:
            res = supabase.table("chats").select("*").eq("user_email", user_email).order("updated_at", desc=True).execute()
            return res.data
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, user_email, created_at, updated_at FROM chats WHERE user_email=? ORDER BY updated_at DESC", (user_email,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "user_email": r[2], "created_at": r[3], "updated_at": r[4]} for r in rows]


def delete_chat(chat_id: int):
    if USE_SUPABASE:
        try:
            supabase.table("messages").delete().eq("chat_id", chat_id).execute()
            supabase.table("chats").delete().eq("id", chat_id).execute()
            return
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
    c.execute("DELETE FROM chats WHERE id=?", (chat_id,))
    conn.commit()
    conn.close()


# ── User functions ────────────────────────────────────────────
def save_user(email: str, display_name: str = ""):
    now = datetime.now().isoformat()
    if USE_SUPABASE:
        try:
            existing = supabase.table("users").select("*").eq("email", email).execute()
            if not existing.data:
                supabase.table("users").insert({
                    "email": email,
                    "display_name": display_name,
                    "created_at": now,
                }).execute()
            return
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (email, display_name, created_at) VALUES (?, ?, ?)",
              (email, display_name, now))
    conn.commit()
    conn.close()


def get_user(email: str):
    if USE_SUPABASE:
        try:
            res = supabase.table("users").select("*").eq("email", email).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    return row


def get_display_name(email: str) -> str:
    if USE_SUPABASE:
        try:
            res = supabase.table("users").select("display_name").eq("email", email).execute()
            if res.data and res.data[0].get("display_name"):
                return res.data[0]["display_name"]
            return ""
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT display_name FROM users WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else ""


def save_display_name(email: str, display_name: str):
    now = datetime.now().isoformat()
    if USE_SUPABASE:
        try:
            existing = supabase.table("users").select("*").eq("email", email).execute()
            if existing.data:
                supabase.table("users").update({"display_name": display_name}).eq("email", email).execute()
            else:
                supabase.table("users").insert({
                    "email": email,
                    "display_name": display_name,
                    "created_at": now,
                }).execute()
            return
        except Exception as e:
            print(f"Supabase error: {e}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (email, display_name, created_at) VALUES (?, ?, ?)",
              (email, display_name, now))
    c.execute("UPDATE users SET display_name=? WHERE email=?", (display_name, email))
    conn.commit()
    conn.close()