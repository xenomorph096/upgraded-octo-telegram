import telebot
import sqlite3
import time
import re
from datetime import datetime, timedelta

# ==============================
# CONFIGURATION
# ==============================
BOT_TOKEN = 8290690728:AAH-ignGcVkF0fM6-oWsidU9qFx6snSjzYo
DB_PATH = dupe_entries.db

bot = telebot.TeleBot(BOT_TOKEN)

# ==============================
# DATABASE SETUP
# ==============================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

cur.execute(
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
)
cur.execute(CREATE INDEX IF NOT EXISTS idx_norm ON entries(normalized_value);)
conn.commit()

# ==============================
# UTILITIES
# ==============================
USERNAME_RE = re.compile(r'@[A-Za-z0-9_]{5,32}$')
PHONE_RE = re.compile(r'^+d[ds-]{5,}$')

def normalize_username(u)
    if not u.startswith(@)
        return None
    u = u[1].lower()
    return u if re.match(r'^[a-z0-9_]{5,32}$', u) else None

def normalize_phone(p)
    p = re.sub(r'[^d+]', '', p)
    if len(re.sub(r'D','',p))  6
        return None
    if not p.startswith('+')
        p = '+' + p
    return p

def is_recent(ts)
    return datetime.now() - datetime.fromtimestamp(ts)  timedelta(hours=24)

def detect_value_type(text)
    text = text.strip()
    if text.startswith(@)
        norm = normalize_username(text)
        if norm
            return (username, norm)
        return (invalid_username, None)
    elif re.match(PHONE_RE, text)
        norm = normalize_phone(text)
        if norm
            return (phone, norm)
        return (invalid_phone, None)
    elif text.isdigit()
        return (telegram_id, text)
    else
        return (None, None)

# ==============================
# BOT HANDLERS
# ==============================
@bot.message_handler(commands=[start, help])
def handle_start(message)
    bot.reply_to(
        message,
        👋 Welcome! Send me a phone number or @username to check if it's a duplicate.n
        I'll tell you if it's already in the database or recently added.nn
        欢迎！发送电话号码或@用户名来检测是否重复。
    )

@bot.message_handler(func=lambda m True)
def handle_input(message)
    raw = message.text.strip()
    user = message.from_user
    chat_id = message.chat.id

    value_type, norm = detect_value_type(raw)

    if value_type == invalid_username
        bot.reply_to(message, ⚠️ Invalid Username Format  用户名格式无效nUsernames must start with @n用户名必须以@开头)
        return
    if value_type == invalid_phone
        bot.reply_to(message, ⚠️ Invalid Phone Format  电话号码格式无效)
        return
    if not value_type
        bot.reply_to(message, ❌ I didn’t detect a valid @username or phone number.n未检测到有效的用户名或电话号码。)
        return

    # Check if already exists
    cur.execute(SELECT submitter_username, ts FROM entries WHERE normalized_value =  AND value_type = , (norm, value_type))
    row = cur.fetchone()

    now_ts = int(time.time())

    if row
        submitter_username, ts = row
        original_time = datetime.fromtimestamp(ts).strftime(%Y-%m-%d %H%M%S)
        bot.reply_to(
            message,
            f⚠️ Duplicate Detected  检测到重复n
            f{'Username' if value_type=='username' else 'Number'} {raw}n
            fOriginally added by {submitter_username or 'Unknown'}n
            fTime {original_time}
        )
        return

    # Insert new record
    cur.execute(
        INSERT INTO entries (submitter_id, submitter_username, chat_id, value_type, raw_value, normalized_value, ts)
        VALUES (, , , , , , )
    , (
        user.id,
        user.username,
        chat_id,
        value_type,
        raw,
        norm,
        now_ts
    ))
    conn.commit()

    added_time = datetime.fromtimestamp(now_ts).strftime(%Y-%m-%d %H%M%S)
    bot.reply_to(
        message,
        f✅ Successfully Added  添加成功n
        f{'Username' if value_type=='username' else 'Number'} {raw}n
        fAdded by {user.username or 'Unknown'}n
        fTime {added_time}
    )

print(🤖 Bot is running on Replit...)
bot.infinity_polling()