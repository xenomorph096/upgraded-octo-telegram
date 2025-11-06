import os
import sqlite3
import time
import re
import logging
from datetime import datetime, timedelta
import telebot

# ==============================
# CONFIGURATION
# ==============================
BOT_TOKEN = os.getenv(8500936015:AAHmkreA99cbgRxpDDGiDBxprlNu5t7ZUTw)
if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN environment variable is not set.")

# Use a persistent folder for database
DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "dupe_entries.db")

# Make sure the folder exists
os.makedirs(DATA_DIR, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN)

# ==============================
# LOGGING
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ==============================
# DATABASE SETUP
# ==============================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS entries(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submitter_id INTEGER,
    submitter_username TEXT,
    chat_id INTEGER,
    value_type TEXT CHECK(value_type IN ('phone','username','telegram_id')),
    raw_value TEXT,
    normalized_value TEXT,
    ts INTEGER
);
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_norm ON entries(normalized_value);")
conn.commit()

# ==============================
# UTILITIES
# ==============================
USERNAME_RE = re.compile(r'@[A-Za-z0-9_]{5,32}$')
PHONE_RE = re.compile(r'^\+?\d[\d\s\-]{5,}$')

def normalize_username(u):
    if not u.startswith("@"):
        return None
    u = u[1:].lower()
    return u if re.match(r'^[a-z0-9_]{5,32}$', u) else None

def normalize_phone(p):
    p = re.sub(r'[^\d+]', '', p)
    if len(re.sub(r'\D','',p)) < 6:
        return None
    if not p.startswith('+'):
        p = '+' + p
    return p

def detect_value_type(text):
    text = text.strip()
    if text.startswith("@"):
        norm = normalize_username(text)
        if norm:
            return ("username", norm)
        return ("invalid_username", None)
    elif re.match(PHONE_RE, text):
        norm = normalize_phone(text)
        if norm:
            return ("phone", norm)
        return ("invalid_phone", None)
    elif text.isdigit():
        return ("telegram_id", text)
    else:
        return (None, None)

def is_recent(ts):
    return datetime.now() - datetime.fromtimestamp(ts) < timedelta(hours=24)

# ==============================
# BOT HANDLERS
# ==============================
@bot.message_handler(commands=["start", "help"])
def handle_start(message):
    bot.reply_to(
        message,
        "👋 Welcome! Send me a phone number or @username to check for duplicates.\n"
        "I'll tell you if it's already in the database or recently added."
    )

@bot.message_handler(func=lambda m: True)
def handle_input(message):
    raw = message.text.strip()
    user = message.from_user
    chat_id = message.chat.id

    value_type, norm = detect_value_type(raw)

    if value_type == "invalid_username":
        bot.reply_to(message, "⚠️ Invalid Username Format. Usernames must start with @.")
        return
    if value_type == "invalid_phone":
        bot.reply_to(message, "⚠️ Invalid Phone Format.")
        return
    if not value_type:
        bot.reply_to(message, "❌ No valid @username or phone number detected.")
        return

    # Check if already exists
    cur.execute("SELECT submitter_username, ts FROM entries WHERE normalized_value = ? AND value_type = ?", (norm, value_type))
    row = cur.fetchone()

    now_ts = int(time.time())

    if row:
        submitter_username, ts = row
        original_time = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        bot.reply_to(
            message,
            f"⚠️ Duplicate Detected\n"
            f"{'Username' if value_type=='username' else 'Number'}: {raw}\n"
            f"Originally added by: {submitter_username or 'Unknown'}\n"
            f"Time: {original_time}"
        )
        logging.info(f"Duplicate detected: {raw} by {user.username}")
        return

    # Insert new record
    cur.execute("""
        INSERT INTO entries (submitter_id, submitter_username, chat_id, value_type, raw_value, normalized_value, ts)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user.id,
        user.username,
        chat_id,
        value_type,
        raw,
        norm,
        now_ts
    ))
    conn.commit()

    added_time = datetime.fromtimestamp(now_ts).strftime("%Y-%m-%d %H:%M:%S")
    bot.reply_to(
        message,
        f"✅ Successfully Added\n"
        f"{'Username' if value_type=='username' else 'Number'}: {raw}\n"
        f"Added by: {user.username or 'Unknown'}\n"
        f"Time: {added_time}"
    )
    logging.info(f"Added: {raw} by {user.username}")

# ==============================
# RUN BOT
# ==============================
logging.info("🤖 Bot is starting...")
bot.infinity_polling()
