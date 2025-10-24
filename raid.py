#!/usr/bin/env python3
"""
Standalone Raid-Smash Script (Telethon)
- Logs in as your Telegram user (creates a session file).
- Listens to a single group (TG_GROUP_ID) for messages from raid bot(s).
- If a raid message containing a tweet link is found, clicks the inline "👊" button
  (or any button whose label contains "👊") and logs the callback feedback.
- Writes events to a JSON log file (tweet_and_raid_log.json).
- Prevents double-smashing the same tweet during the same runtime (in-memory).
--
HOW TO USE:
1. Install dependencies:
   pip install telethon

2. Edit the CONFIG section below:
   - TG_API_ID, TG_API_HASH: from my.telegram.org
   - SESSION: session filename prefix (e.g., "session")
   - TG_GROUP_ID: group id where raids appear (integer, negative for supergroups)
   - RAID_BOT_IDS: list of raid bot numeric IDs

3. Run:
   python raid_smash.py
   The first run will prompt you to log in (phone number + confirmation code).
"""

import os
import json
import re
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, functions

# ===================== CONFIG - EDIT THESE =====================
TG_API_ID = 27403368                # <- REPLACE with your API ID (integer)
TG_API_HASH = "7cfc7759b82410f5d90641d6a6fc415f"     # <- REPLACE with your API HASH (string)
SESSION = "session"               # session file prefix (e.g., "session")
TG_GROUP_ID = -1002325443922      # <- REPLACE with the group ID you watch (integer)
RAID_BOT_IDS = [8004181615]       # <- REPLACE with the raid bot's Telegram numeric ID(s)
LOG_FILE = "tweet_and_raid_log.json"
# ===================== END CONFIG =================================

# Create Telethon client
client = TelegramClient(SESSION, TG_API_ID, TG_API_HASH)

# In-memory set to avoid double-smash during runtime
smashed_tweet_ids = set()

# Regex to extract tweet URL and tweet id from message text
TWEET_RE = re.compile(
    r"(https?://(?:t.co|(?:mobile\.)?twitter\.com|(?:www\.)?twitter\.com|x\.com)/[^\s]+/status(?:es)?/(\d+))",
    re.IGNORECASE
)


def now_iso():
    return datetime.utcnow().isoformat() + "Z"


def save_json_append(path, entry):
    """
    Append an entry (dict) to a JSON array file. Creates file if missing.
    Falls back to newline-delimited JSON if the file is corrupted.
    """
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
                # fallback: append newline-delimited JSON
                f.close()
                with open(path, "a", encoding="utf-8") as fa:
                    fa.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"⚠️ Failed to save log entry: {e}")


def extract_tweet(text):
    """
    Return (tweet_url, tweet_id) if found in text, else (None, None).
    """
    if not text:
        return None, None
    m = TWEET_RE.search(text)
    if m:
        return m.group(1), m.group(2)
    return None, None


async def click_inline_button(client_obj, message, match_texts=("👊",)):
    """
    Find an inline button whose label contains any of match_texts (case-insensitive),
    trigger the button callback, and return a result dict with feedback.
    """
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
    """
    Listen for new messages in the configured group. If the message sender is in RAID_BOT_IDS
    and the message contains a tweet URL, click the '👊' button if present, log feedback,
    and avoid double-smashing the same tweet ID during runtime.
    """
    try:
        msg = event.message
        # get sender (bot) id
        sender = await event.get_sender()
        sender_id = getattr(sender, "id", None)
        if not sender_id or sender_id not in RAID_BOT_IDS:
            return  # ignore messages not from the configured raid bot(s)

        text = (msg.text or "") + " " + " ".join(att.url for att in getattr(msg, "media", []) or [])
        tweet_url, tweet_id = extract_tweet(msg.text or "")
        if not tweet_id:
            # Some bots may include the tweet link in entities/media or caption; try full message string too
            tweet_url, tweet_id = extract_tweet(str(msg))
        if not tweet_id:
            return  # no tweet URL found

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

        feedback = click_result.get('callback_result') or click_result.get('error') or click_result.get('reason')
        print(f"🔘 Raid smashed: {tweet_url}, feedback: {feedback}")

    except Exception as e:
        print("❌ raid_handler error:", repr(e))


async def main():
    print("🚀 Starting Raid-Smash client...")
    await client.start()
    me = await client.get_me()
    print(f"✅ Logged in as: {getattr(me, 'username', getattr(me, 'first_name', 'Unknown'))}")
    print(f"Listening for raids in group {TG_GROUP_ID} from bot IDs {RAID_BOT_IDS} ...")
    # run until disconnected
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting on user interrupt.")