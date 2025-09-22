import asyncio
import os
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram import BaseMiddleware
from aiogram.exceptions import (
    TelegramNetworkError, 
    TelegramConflictError, 
    TelegramBadRequest,
    TelegramUnauthorizedError
)
from flask import Flask
import threading
from typing import Callable, Dict, Any, Awaitable
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
BOT_TOKEN = "7834289309:AAEEvwQ_cqjzdpC85bA9Z0hrfOBaTJhozcM"

if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable is not set!")
    raise ValueError("BOT_TOKEN environment variable is required")

# Validate token format
import re
token_pattern = r'^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$'
if not re.match(token_pattern, BOT_TOKEN):
    logger.error("Invalid bot token format!")
    raise ValueError("Bot token format is invalid")

# Your channel/group IDs where the bot should work
ALLOWED_CHAT_IDS = [-1002942557942]

# Create custom session with longer timeout
session = AiohttpSession(timeout=180.0)

async def validate_bot_token(token: str) -> bool:
    """Validate bot token by calling getMe API"""
    try:
        temp_bot = Bot(token=token, session=AiohttpSession(timeout=30.0))
        me = await temp_bot.get_me()
        await temp_bot.session.close()
        logger.info(f"Bot token validated successfully. Bot: @{me.username}")
        return True
    except TelegramUnauthorizedError:
        logger.error("Bot token is invalid or unauthorized")
        return False
    except Exception as e:
        logger.error(f"Error validating bot token: {e}")
        return False

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

# Enhanced Retry Middleware
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
            except TelegramUnauthorizedError:
                logger.error("Unauthorized error - check your bot token!")
                break
            except (TelegramNetworkError, TelegramBadRequest) as e:
                if attempt == self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) reached: {e}")
                    try:
                        await event.answer("⚠️ Service temporarily unavailable. Please try again later.")
                    except Exception:
                        pass
                    return None
                else:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

# Apply retry middleware
dp.message.middleware(RetryMiddleware(max_retries=3, retry_delay=1.0))

# Helper functions (keep your existing helper functions)
def format_time_left(seconds: int) -> str:
    h, m = divmod(seconds, 3600)
    m, s = divmod(m, 60)
    return f"{h:02d}h {m:02d}min"

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

async def is_chat_allowed(chat_id: int) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return chat_id in ALLOWED_CHAT_IDS

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

async def safe_reply(message: Message, text: str, timeout: float = 30.0):
    try:
        return await asyncio.wait_for(
            message.reply(text),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"Reply timeout for message {getattr(message, 'message_id', None)}")
    except TelegramUnauthorizedError:
        logger.error("Unauthorized error - bot token is invalid!")
        raise
    except TelegramNetworkError as e:
        logger.warning(f"Network error in reply: {e}")
    except TelegramBadRequest as e:
        logger.error(f"Telegram API error in reply: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in reply: {e}")
    return None

async def safe_edit(message: types.Message, text: str, timeout: float = 30.0):
    try:
        return await asyncio.wait_for(
            message.edit_text(text),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"Edit timeout for message {getattr(message, 'message_id', None)}")
    except TelegramUnauthorizedError:
        logger.error("Unauthorized error - bot token is invalid!")
        raise
    except TelegramNetworkError as e:
        logger.warning(f"Network error in edit: {e}")
    except TelegramBadRequest as e:
        if "not enough rights" in str(e).lower() or "message to edit not found" in str(e).lower():
            logger.error(f"Permission error - cannot edit message: {e}")
            try:
                return await asyncio.wait_for(
                    message.answer(text),
                    timeout=timeout
                )
            except Exception:
                pass
        else:
            logger.error(f"Telegram API error in edit: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in edit: {e}")
    return None

# Store active timers to prevent multiple timers per chat
active_timers = {}

# Keep your existing command handlers (/time, /sleep, /cancel) unchanged
# ... (your existing command handler code) ...

def run_flask():
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

async def main():
    # Validate bot token before starting
    logger.info("Validating bot token...")
    if not await validate_bot_token(BOT_TOKEN):
        logger.error("Bot token validation failed! Please check your token.")
        return

    # Delete any existing webhook to avoid conflicts
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted successfully")
    except TelegramUnauthorizedError:
        logger.error("Unauthorized error when deleting webhook - check your bot token!")
        return
    except Exception as e:
        logger.warning(f"Could not delete webhook: {e}")

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask health check server started")

    while True:
        try:
            logger.info("Starting bot polling...")
            await dp.start_polling(
                bot,
                polling_timeout=30,
                request_timeout=60,
                skip_updates=True,
                allowed_updates=["message", "channel_post"],
                close_bot_session=False
            )
        except TelegramUnauthorizedError:
            logger.error("CRITICAL: Bot token is unauthorized! Check your token and regenerate if needed.")
            break
        except TelegramConflictError as e:
            logger.error(f"Conflict error: {e}. Another instance might be running. Restarting in 10 seconds...")
            await asyncio.sleep(10)
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
    print("- Commands: /time, /sleep, and /cancel")
    print("- Health check server on port 8000")
    print("- Auto-retry and graceful error handling")
    print("- Enhanced token validation")

    asyncio.run(main())
