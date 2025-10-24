#!/usr/bin/env python3
"""
Raid-Smash Script + Dummy Webhook (Render-compatible)
------------------------------------------------------
- Telethon client listens for raid messages.
- Flask web app runs alongside as a dummy website/webhook endpoint.
  (Used to keep Render/Railway services alive or respond to external pings.)
"""

import os
import json
import re
import asyncio
import threading
from datetime import datetime
from telethon import TelegramClient, events, functions
from flask import Flask, jsonify, request

# ===================== CONFIG - EDIT THESE =====================
TG_API_ID = 27403368
TG_API_HASH = "7cfc7759b82410f5d90641d6a6fc415f"
SESSION = "session"
TG_GROUP_ID = -1002325443922
RAID_BOT_IDS = [8004181615]
LOG_FILE = "tweet_and_raid_log.json"
PORT = int(os.getenv("PORT", 8080))  # Render sets PORT automatically
# ===================== END CONFIG ===============================

client = TelegramClient(SESSION, TG_API_ID, TG_API_HASH)
smashed_tweet_ids = set()

TWEET_RE = re.compile(
    r"(https?://(?:t.co|(?:mobile\.)?twitter\.com|(?:www\.)?twitter\.com|x\.com)/[^\s]+/status(?:es)?/(\d+))",
    re.IGNORECASE
)

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "Dummy webhook online 🚀"})

@app.route("/listener", methods=["POST", "GET"])
def listener():
    data = request.get_json(silent=True) or {}
    print("📩 Received dummy webhook:", data)
    return jsonify({"received": True, "data": data, "message": "Listening ✅"})

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def save_json_append(path, entry):
    try:
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump([], f)
        with open(path, "r+", encoding="utf-8") as f:
            try:
                arr = json.load(f)
                if not isinstance(arr, list):
                    arr = []
                arr.append(entry)
                f.seek(0)
                json.dump(arr, f, indent=2)
                f.truncate()
            except json.JSONDecodeError:
                f.close()
                with open(path, "a", encoding="utf-8") as fa:
                    fa.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"⚠️ Failed to save log entry: {e}")

def extract_tweet(text):
    if not text:
        return None, None
    m = TWEET_RE.search(text)
    if m:
        return m.group(1), m.group(2)
    return None, None

async def click_inline_button(client_obj, message, match_texts=("👊",)):
    buttons = getattr(message, "buttons", None) or getattr(message, "reply_markup", None)
    if not buttons:
        return {"clicked": False, "reason": "no_buttons"}
    for row in buttons:
        for btn in row:
            lbl = getattr(btn, "text", "") or ""
            try:
                label_lower = lbl.lower()
            except Exception:
                label_lower = ""
            if any(mt.lower() in label_lower for mt in match_texts):
                try:
                    res = await client_obj(functions.messages.GetBotCallbackAnswerRequest(
                        peer=message.to_id,
                        msg_id=message.id,
                        data=btn.data or b""
                    ))
                    return {"clicked": True, "button_text": lbl, "callback_result": str(res)}
                except Exception as e:
                    return {"clicked": False, "button_text": lbl, "error": repr(e)}
    return {"clicked": False, "reason": "no_matching_label"}

@client.on(events.NewMessage(chats=[TG_GROUP_ID], incoming=True))
async def raid_handler(event):
    try:
        msg = event.message
        sender = await event.get_sender()
        sender_id = getattr(sender, "id", None)
        if not sender_id or sender_id not in RAID_BOT_IDS:
            return

        text = (msg.text or "") + " " + " ".join(att.url for att in getattr(msg, "media", []) or [])
        tweet_url, tweet_id = extract_tweet(msg.text or "")
        if not tweet_id:
            tweet_url, tweet_id = extract_tweet(str(msg))
        if not tweet_id:
            return

        if tweet_id in smashed_tweet_ids:
            print(f"⚠️ Already smashed (runtime): {tweet_url}")
            return

        click_result = await click_inline_button(client, msg, match_texts=("👊",))
        smashed_tweet_ids.add(tweet_id)

        entry = {
            "time": now_iso(),
            "type": "raid_smash",
            "chat_id": event.chat_id,
            "message_id": msg.id,
            "tweet_url": tweet_url,
            "tweet_id": tweet_id,
            "smash": click_result
        }
        save_json_append(LOG_FILE, entry)
        print(f"🔘 Raid smashed: {tweet_url}")
    except Exception as e:
        print("❌ raid_handler error:", repr(e))

async def telethon_worker():
    await client.start()
    me = await client.get_me()
    print(f"✅ Logged in as {me.username or me.first_name}")
    await client.run_until_disconnected()

def start_flask():
    print(f"🌐 Dummy site running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    try:
        asyncio.run(telethon_worker())
    except KeyboardInterrupt:
        print("\n👋 Exiting cleanly.")
