import asyncio
from datetime import datetime, timedelta
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramNetworkError
from flask import Flask
import threading
import os
from typing import Callable, Dict, Any, Awaitable
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Replace with your bot token
BOT_TOKEN = "7834289309:AAFI_mkLG2N7lvb5HiVaJJrkBH4COcixUYs"

# Your channel/group IDs where the bot should work
ALLOWED_CHAT_IDS = [-1002942557942]  # Add your specific channel/group IDs here

# Create custom session with longer timeout
session = AiohttpSession(timeout=180.0)  # 3 minutes overall timeout

bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

# Flask app for health checks
app = Flask(__name__)

@app.route('/')
def health_check():
    return 'Bot is running!', 200

@app.route('/health')
def health():
    return {'status': 'healthy', 'bot': 'online'}, 200

# Retry Middleware for handling network errors
class RetryMiddleware(BaseMiddleware):
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        super().__init__()
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        for attempt in range(self.max_retries + 1):
            try:
                return await handler(event, data)
            except TelegramNetworkError as e:
                if attempt == self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) reached for message {getattr(event, 'message_id', None)}: {e}")
                    try:
                        await event.answer("⚠️ Network error occurred. Please try again later.", parse_mode=ParseMode.HTML)
                    except Exception:
                        pass
                    return None
                else:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Network error on attempt {attempt + 1}, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Non-network error in handler: {e}")
                raise

# Apply retry middleware
dp.message.middleware(RetryMiddleware(max_retries=3, retry_delay=1.0))

# Helper: format time left nicely (hours:minutes only)
def format_time_left(seconds: int) -> str:
    h, m = divmod(seconds, 3600)
    m, s = divmod(m, 60)
    return f"<b>{h:02d}h {m:02d}min</b>"

# Parse hours:minutes
def parse_time_arg(arg: str) -> timedelta:
    try:
        if ":" in arg:
            parts = arg.split(":")
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
        else:
            hours = int(arg)
            minutes = 0

        if hours < 0 or minutes < 0:
            raise ValueError("Time values cannot be negative")

        return timedelta(hours=hours, minutes=minutes)
    except (ValueError, IndexError):
        raise ValueError("Invalid time format. Use format: H or H:M")

# Check if chat is allowed
async def is_chat_allowed(chat_id: int) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return chat_id in ALLOWED_CHAT_IDS

# Check if user is admin in group
async def is_user_admin(message: Message) -> bool:
    try:
        if message.chat.type in ["group", "supergroup"]:
            user = message.from_user
            chat_member = await bot.get_chat_member(message.chat.id, user.id)
            return chat_member.status in ["administrator", "creator"]
        return True
    except Exception as e:
        logger.error(f"Error checking user admin status: {e}")
        return False

# Safe send/edit wrappers
async def safe_reply(message: Message, text: str, parse_mode=ParseMode.HTML, timeout: float = 30.0):
    try:
        return await asyncio.wait_for(
            message.reply(text, parse_mode=parse_mode),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"Reply timeout for message {getattr(message, 'message_id', None)}")
    except TelegramNetworkError as e:
        logger.warning(f"Network error in reply: {e}")
    return None

async def safe_edit(message: types.Message, text: str, parse_mode=ParseMode.HTML, timeout: float = 30.0):
    try:
        return await asyncio.wait_for(
            message.edit_text(text, parse_mode=parse_mode),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"Edit timeout for message {getattr(message, 'message_id', None)}")
    except TelegramNetworkError as e:
        logger.warning(f"Network error in edit: {e}")
    return None

# /time command
@dp.message(Command("time"))
async def time_command(message: Message):
    if not await is_chat_allowed(message.chat.id):
        return
    if message.chat.type in ["group", "supergroup"] and not await is_user_admin(message):
        await safe_reply(message, "<b>ACCESS DENIED</b>\n\nOnly administrators can use this command.")
        return

    args = message.text.split()[1:]
    if not args:
        await safe_reply(message,
            "<b>TIME COMMAND USAGE</b>\n\n"
            "Format: <code>/time <duration></code>\n"
            "Examples:\n"
            "• <code>/time 1</code> - 1 hour\n"
            "• <code>/time 1:30</code> - 1 hour 30 minutes\n\n"
            "<i>Sets an online status timer</i>"
        )
        return

    try:
        delta = parse_time_arg(args[0])
    except ValueError as e:
        await safe_reply(message, f"<b>ERROR</b>\n\n{e}")
        return

    end_time = datetime.now() + delta

    msg = await safe_reply(message,
        "<b>ONLINE ACTIVE SESSION</b>\n\n"
        "<b>Status:</b> Collecting Cases\n"
        "<b>Time Remaining:</b> Calculating...\n\n"
        "<b>Contact:</b> @OguMarco"
    )
    if not msg:
        return

    async def countdown():
        try:
            while True:
                remaining = int((end_time - datetime.now()).total_seconds())
                if remaining <= 0:
                    await safe_edit(msg,
                        "<b>SESSION COMPLETED</b>\n\n"
                        "<b>Status:</b> Representative Offline\n"
                        "<b>Action:</b> Session Concluded\n\n"
                        "<b>Contact:</b> @OguMarco\n\n"
                        "<i>Use /time to start a new session</i>"
                    )
                    break
                time_left = format_time_left(remaining)
                result = await safe_edit(msg,
                    "<b>ONLINE ACTIVE SESSION</b>\n\n"
                    "<b>Status:</b> Collecting Cases\n"
                    f"<b>Time Remaining:</b> {time_left}\n\n"
                    "<b>Contact:</b> @OguMarco"
                )
                if result is None:
                    logger.warning("Edit failed, stopping countdown")
                    break
                await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error in countdown: {e}")

    asyncio.create_task(countdown())

# /sleep command
@dp.message(Command("sleep"))
async def sleep_command(message: Message):
    if not await is_chat_allowed(message.chat.id):
        return
    if message.chat.type in ["group", "supergroup"] and not await is_user_admin(message):
        await safe_reply(message, "<b>ACCESS DENIED</b>\n\nOnly administrators can use this command.")
        return

    args = message.text.split()[1:]
    if not args:
        await safe_reply(message,
            "<b>SLEEP MODE COMMAND USAGE</b>\n\n"
            "Format: <code>/sleep <duration></code>\n"
            "Examples:\n"
            "• <code>/sleep 8</code> - 8 hours\n"
            "• <code>/sleep 7:30</code> - 7 hours 30 minutes\n\n"
            "<i>Sets a sleep mode timer</i>"
        )
        return

    try:
        delta = parse_time_arg(args[0])
    except ValueError as e:
        await safe_reply(message, f"<b>ERROR</b>\n\n{e}")
        return

    end_time = datetime.now() + delta

    msg = await safe_reply(message,
        "<b>SLEEP MODE ACTIVATED</b>\n\n"
        "<b>Status:</b> Offline - Sleeping\n"
        "<b>Time Remaining:</b> Calculating...\n\n"
        "<b>Contact After:</b> @OguMarco"
    )
    if not msg:
        return

    async def countdown():
        try:
            while True:
                remaining = int((end_time - datetime.now()).total_seconds())
                if remaining <= 0:
                    await safe_edit(msg,
                        "<b>SLEEP MODE COMPLETED</b>\n\n"
                        "<b>Status:</b> Online - Active\n"
                        "<b>Action:</b> Ready To Collect Cases\n\n"
                        "<b>Contact:</b> @OguMarco"
                    )
                    break
                time_left = format_time_left(remaining)
                result = await safe_edit(msg,
                    "<b>SLEEP MODE ACTIVE</b>\n\n"
                    "<b>Status:</b> Offline - Sleeping\n"
                    f"<b>Time Remaining:</b> {time_left}\n\n"
                    "<b>Contact After:</b> @OguMarco"
                )
                if result is None:
                    logger.warning("Edit failed, stopping countdown")
                    break
                await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error in countdown: {e}")

    asyncio.create_task(countdown())

# Handle channel posts
@dp.channel_post()
async def handle_channel_post(message: Message):
    if not await is_chat_allowed(message.chat.id):
        return
    
    # Check if the message contains commands
    if message.text and message.text.startswith('/time'):
        await time_command(message)
    elif message.text and message.text.startswith('/sleep'):
        await sleep_command(message)

def run_flask():
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)

async def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    while True:
        try:
            logger.info("Starting bot polling...")
            await dp.start_polling(
                bot,
                polling_timeout=20,
                request_timeout=60,
                skip_updates=True,
                allowed_updates=["message", "channel_post"]
            )
        except asyncio.TimeoutError:
            logger.warning("Polling timeout occurred, restarting in 3 seconds...")
            await asyncio.sleep(3)
        except TelegramNetworkError as e:
            logger.error(f"Network error during polling: {e}, restarting in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected polling error: {e}, restarting in 10 seconds...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    print("Professional Timer Bot is starting...")
    print("- Commands: /time and /sleep")
    print("- Health check server on port 8000")
    print("- Auto-retry and graceful error handling")

    asyncio.run(main())
