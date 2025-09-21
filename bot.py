import asyncio
from datetime import datetime, timedelta
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramNetworkError, TelegramConflictError, TelegramBadRequest
from flask import Flask
import threading
import os
from typing import Callable, Dict, Any, Awaitable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Replace with your bot token
BOT_TOKEN = "7834289309:AAEEvwQ_cqjzdpC85bA9Z0hrfOBaTJhozcM"

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
            except (TelegramNetworkError, TelegramBadRequest) as e:
                if attempt == self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) reached for message {getattr(event, 'message_id', None)}: {e}")
                    try:
                        await event.answer("⚠️ Error occurred. Please try again later.")
                    except Exception:
                        pass
                    return None
                else:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Error on attempt {attempt + 1}, retrying in {delay}s: {e}")
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
    return f"{h:02d}h {m:02d}min"

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
async def safe_reply(message: Message, text: str, timeout: float = 30.0):
    try:
        return await asyncio.wait_for(
            message.reply(text),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"Reply timeout for message {getattr(message, 'message_id', None)}")
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
    except TelegramNetworkError as e:
        logger.warning(f"Network error in edit: {e}")
    except TelegramBadRequest as e:
        # Check if it's a permission error
        if "not enough rights" in str(e).lower() or "message to edit not found" in str(e).lower():
            logger.error(f"Permission error - cannot edit message: {e}")
            # Try to send a new message instead
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

# /time command
@dp.message(Command("time"))
async def time_command(message: Message):
    if not await is_chat_allowed(message.chat.id):
        return
    if message.chat.type in ["group", "supergroup"] and not await is_user_admin(message):
        await safe_reply(message, "ACCESS DENIED\n\nOnly administrators can use this command.")
        return

    args = message.text.split()[1:]
    if not args:
        await safe_reply(message,
            "TIME COMMAND USAGE\n\n"
            "Format: /time <duration>\n"
            "Examples:\n"
            "• /time 1 - 1 hour\n"
            "• /time 1:30 - 1 hour 30 minutes\n\n"
            "Sets an online status timer"
        )
        return

    # Cancel any existing timer for this chat
    chat_id = message.chat.id
    if chat_id in active_timers:
        active_timers[chat_id].cancel()
        del active_timers[chat_id]
        await asyncio.sleep(1)  # Brief pause to ensure cancellation

    try:
        delta = parse_time_arg(args[0])
    except ValueError as e:
        await safe_reply(message, f"ERROR\n\n{e}")
        return

    end_time = datetime.now() + delta

    msg = await safe_reply(message,
        "🟢 ONLINE ACTIVE SESSION\n\n"
        "Status: Collecting Cases\n"
        "Time Remaining: Calculating...\n\n"
        "Contact: @OguMarco"
    )
    if not msg:
        logger.error("Failed to send initial time message")
        return

    logger.info(f"Started time timer for chat {chat_id} with duration {delta}")

    async def countdown():
        last_message = msg  # Keep track of the last message
        try:
            while True:
                remaining = int((end_time - datetime.now()).total_seconds())
                if remaining <= 0:
                    final_msg = await safe_edit(last_message,
                        "✅ SESSION COMPLETED\n\n"
                        "Status: Representative Offline\n"
                        "Action: Session Concluded\n\n"
                        "Contact: @OguMarco\n\n"
                        "Use /time to start a new session"
                    )
                    if chat_id in active_timers:
                        del active_timers[chat_id]
                    break
                
                time_left = format_time_left(remaining)
                result = await safe_edit(last_message,
                    "🟢 ONLINE ACTIVE SESSION\n\n"
                    "Status: Collecting Cases\n"
                    f"Time Remaining: {time_left}\n\n"
                    "Contact: @OguMarco"
                )
                
                # If edit failed, try sending a new message
                if result is None:
                    logger.warning("Edit failed, trying to send new message")
                    new_msg = await safe_reply(message,
                        "🟢 ONLINE ACTIVE SESSION\n\n"
                        "Status: Collecting Cases\n"
                        f"Time Remaining: {time_left}\n\n"
                        "Contact: @OguMarco"
                    )
                    if new_msg:
                        last_message = new_msg
                
                await asyncio.sleep(30)  # Update every 30 seconds
        except asyncio.CancelledError:
            logger.info(f"Timer cancelled for chat {chat_id}")
            await safe_edit(last_message, 
                "⏹️ TIMER CANCELLED\n\n"
                "Status: Session Interrupted\n"
                "Action: Timer Stopped Manually\n\n"
                "Contact: @OguMarco"
            )
        except Exception as e:
            logger.error(f"Error in countdown: {e}")
            if chat_id in active_timers:
                del active_timers[chat_id]

    # Store the task and start it
    task = asyncio.create_task(countdown())
    active_timers[chat_id] = task

# /sleep command
@dp.message(Command("sleep"))
async def sleep_command(message: Message):
    if not await is_chat_allowed(message.chat.id):
        return
    if message.chat.type in ["group", "supergroup"] and not await is_user_admin(message):
        await safe_reply(message, "ACCESS DENIED\n\nOnly administrators can use this command.")
        return

    args = message.text.split()[1:]
    if not args:
        await safe_reply(message,
            "SLEEP MODE COMMAND USAGE\n\n"
            "Format: /sleep <duration>\n"
            "Examples:\n"
            "• /sleep 8 - 8 hours\n"
            "• /sleep 7:30 - 7 hours 30 minutes\n\n"
            "Sets a sleep mode timer"
        )
        return

    # Cancel any existing timer for this chat
    chat_id = message.chat.id
    if chat_id in active_timers:
        active_timers[chat_id].cancel()
        del active_timers[chat_id]
        await asyncio.sleep(1)  # Brief pause to ensure cancellation

    try:
        delta = parse_time_arg(args[0])
    except ValueError as e:
        await safe_reply(message, f"ERROR\n\n{e}")
        return

    end_time = datetime.now() + delta

    msg = await safe_reply(message,
        "🌙 SLEEP MODE ACTIVATED\n\n"
        "Status: Offline - Sleeping\n"
        "Time Remaining: Calculating...\n\n"
        "Contact After: @OguMarco"
    )
    if not msg:
        logger.error("Failed to send sleep mode message")
        return

    logger.info(f"Starting sleep timer for {delta} in chat {chat_id}")

    async def countdown():
        last_message = msg  # Keep track of the last message
        try:
            while True:
                remaining = int((end_time - datetime.now()).total_seconds())
                if remaining <= 0:
                    final_msg = await safe_edit(last_message,
                        "☀️ SLEEP MODE COMPLETED\n\n"
                        "Status: Online - Active\n"
                        "Action: Ready To Collect Cases\n\n"
                        "Contact: @OguMarco"
                    )
                    if chat_id in active_timers:
                        del active_timers[chat_id]
                    break
                
                time_left = format_time_left(remaining)
                result = await safe_edit(last_message,
                    "🌙 SLEEP MODE ACTIVE\n\n"
                    "Status: Offline - Sleeping\n"
                    f"Time Remaining: {time_left}\n\n"
                    "Contact After: @OguMarco"
                )
                
                # If edit failed, try sending a new message
                if result is None:
                    logger.warning("Edit failed, trying to send new message")
                    new_msg = await safe_reply(message,
                        "🌙 SLEEP MODE ACTIVE\n\n"
                        "Status: Offline - Sleeping\n"
                        f"Time Remaining: {time_left}\n\n"
                        "Contact After: @OguMarco"
                    )
                    if new_msg:
                        last_message = new_msg
                
                await asyncio.sleep(30)  # Update every 30 seconds
        except asyncio.CancelledError:
            logger.info(f"Sleep timer cancelled for chat {chat_id}")
            await safe_edit(last_message, 
                "⏹️ SLEEP MODE CANCELLED\n\n"
                "Status: Online - Active\n"
                "Action: Sleep Timer Stopped\n\n"
                "Contact: @OguMarco"
            )
        except Exception as e:
            logger.error(f"Error in sleep countdown: {e}")
            if chat_id in active_timers:
                del active_timers[chat_id]

    # Store the task and start it
    task = asyncio.create_task(countdown())
    active_timers[chat_id] = task
    logger.info(f"Sleep timer started successfully for chat {chat_id}")

# /cancel command to stop active timers
@dp.message(Command("cancel"))
async def cancel_command(message: Message):
    if not await is_chat_allowed(message.chat.id):
        return
    if message.chat.type in ["group", "supergroup"] and not await is_user_admin(message):
        await safe_reply(message, "ACCESS DENIED\n\nOnly administrators can use this command.")
        return

    chat_id = message.chat.id
    if chat_id in active_timers:
        active_timers[chat_id].cancel()
        del active_timers[chat_id]
        await safe_reply(message, "✅ TIMER CANCELLED\n\nActive timer has been stopped.")
        logger.info(f"Cancelled timer for chat {chat_id}")
    else:
        await safe_reply(message, "❌ NO ACTIVE TIMER\n\nThere is no active timer to cancel.")

# Handle channel posts
@dp.channel_post()
async def handle_channel_post(message: Message):
    if not await is_chat_allowed(message.chat.id):
        return
    
    # Check if the message contains commands
    if message.text:
        if message.text.startswith('/time'):
            await time_command(message)
        elif message.text.startswith('/sleep'):
            await sleep_command(message)
        elif message.text.startswith('/cancel'):
            await cancel_command(message)

def run_flask():
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

async def main():
    # Delete any existing webhook to avoid conflicts
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted successfully")
    except Exception as e:
        logger.warning(f"Could not delete webhook: {e}")

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

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

    asyncio.run(main())
