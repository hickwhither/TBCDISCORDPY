import os

from dotenv import load_dotenv

load_dotenv()

BOT_ID = os.environ["BOT_ID"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
PREFIX = os.environ["PREFIX"]
LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "0"))
