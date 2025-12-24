
import os
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = "data/medflix_userbot"

async def check_auth():
    print(f"Checking session: {SESSION_NAME}.session")
    client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ NOT AUTHORIZED. Login required.")
            return False
        
        me = await client.get_me()
        print(f"✅ AUTHORIZED as: {me.username or me.first_name}")
        return True
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(check_auth())
