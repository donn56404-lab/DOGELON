#!/usr/bin/env python3
"""
Raid Smash Listener (Render-ready, Safe Version)
------------------------------------------------
✅ Listens for raid messages in one group
✅ Clicks the 👊 button automatically
✅ Avoids smashing the same tweet twice
✅ Logs and prints callback results
✅ Keeps a dummy Flask site running for Render
"""

import os
import re
import json
import asyncio
import threading
from telethon import TelegramClient, events, functions
from flask import Flask, jsonify

# ====== CONFIG ======
TG_API_ID = 27403368
TG_API_HASH = "7cfc7759b82410f5d90641d6a6fc415f"
SESSION = "session"
TG_GROUP_ID = -1002325443922
RAID_BOT_IDS = [8004181615]
PORT = int(os.getenv("PORT", 8080))
LOG_FILE = "smashed_links.json"
# =====================

client = TelegramClient(SESSION, TG_API_ID, TG_API_HASH)
app = Flask(__name__)

# Regex to detect tweet/x.com links
TWEET_RE = re.compile(r"(https?://(?:x\.com|twitter\.com)/[^\s]+/status(?:es)?/(\d+))", re.IGNORECASE)

# Load previously smashed tweet IDs
def load_smashed_links():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_smashed_links():
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(list(smashed_links), f, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to save smashed links: {e}")

smashed_links = load_smashed_links()

@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "🚀 Dummy Flask site running fine."})

@app.route("/ping")
def ping():
    return jsonify({"alive": True, "smashed_count": len(smashed_links)})

def extract_tweet_id(text):
    if not text:
        return None, None
    m = TWEET_RE.search(text)
    if m:
        return m.group(1), m.group(2)
    return None, None

async def click_smash_button(msg):
    """Find and click the 👊 button, print callback result."""
    buttons = getattr(msg, "buttons", None)
    if not buttons:
        return "no_buttons"

    for row in buttons:
        for btn in row:
            if "👊" in (btn.text or ""):
                try:
                    res = await client(functions.messages.GetBotCallbackAnswerRequest(
                        peer=msg.to_id,
                        msg_id=msg.id,
                        data=btn.data or b""
                    ))
                    print(f"✅ Smashed {msg.id} | Callback: {res}")
                    return "clicked"
                except Exception as e:
                    print(f"⚠️ Smash error: {e}")
                    return "error"
    return "no_match"

@client.on(events.NewMessage(chats=[TG_GROUP_ID], incoming=True))
async def raid_listener(event):
    """Main raid listener."""
    try:
        msg = event.message
        sender = await event.get_sender()
        if sender.id not in RAID_BOT_IDS:
            return

        text = msg.text or ""
        tweet_url, tweet_id = extract_tweet_id(text)
        if not tweet_id:
            return

        # Skip if already smashed
        if tweet_id in smashed_links:
            print(f"⚠️ Already smashed: {tweet_url}")
            return

        result = await click_smash_button(msg)
        if result == "clicked":
            smashed_links.add(tweet_id)
            save_smashed_links()
            print(f"💾 Recorded smashed tweet: {tweet_url}")
    except Exception as e:
        print(f"❌ Listener error: {e}")

async def run_telethon():
    await client.start()
    me = await client.get_me()
    print(f"✅ Logged in as {me.username or me.first_name}")
    await client.run_until_disconnected()

def run_flask():
    print(f"🌐 Dummy site running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(run_telethon())
