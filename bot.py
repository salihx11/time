import asyncio
from datetime import datetime, timedelta
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Replace with your bot token
BOT_TOKEN = "7834289309:AAFI_mkLG2N7lvb5HiVaJJrkBH4COcixUYs"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Store last message IDs for deletion
user_last_messages = {}

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

# Check if user is admin in group
async def is_user_admin(message: Message) -> bool:
    try:
        if message.chat.type in ["group", "supergroup"]:
            user = message.from_user
            chat_member = await bot.get_chat_member(message.chat.id, user.id)
            return chat_member.status in ["administrator", "creator"]
        return True  # For private chats and channels, assume admin
    except Exception as e:
        logger.error(f"Error checking user admin status: {e}")
        return False

# Delete previous bot message for user
async def delete_previous_message(chat_id: int):
    try:
        if chat_id in user_last_messages:
            await bot.delete_message(chat_id, user_last_messages[chat_id])
            del user_last_messages[chat_id]
    except Exception as e:
        logger.error(f"Error deleting previous message: {e}")

# /time command
@dp.message(Command("time"))
async def time_command(message: Message):
    # Check if user is admin in groups
    if message.chat.type in ["group", "supergroup"] and not await is_user_admin(message):
        await message.answer("<b>ACCESS DENIED</b>\n\nOnly administrators can use this command.", parse_mode=ParseMode.HTML)
        return
    
    args = message.text.split()[1:]
    if not args:
        await message.answer(
            "<b>TIME COMMAND USAGE</b>\n\n"
            "Format: <code>/time &lt;duration&gt;</code>\n"
            "Examples:\n"
            "• <code>/time 1</code> - 1 hour\n"
            "• <code>/time 1:30</code> - 1 hour 30 minutes\n\n"
            "<i>Sets an online status timer</i>",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        delta = parse_time_arg(args[0])
    except ValueError as e:
        await message.answer(f"<b>ERROR</b>\n\n{e}", parse_mode=ParseMode.HTML)
        return

    # Delete previous bot message
    await delete_previous_message(message.chat.id)

    end_time = datetime.now() + delta
    
    msg = await message.reply(
        "<b>ONLINE ACTIVE SESSION</b>\n\n"
        "<b>Status:</b> Collecting Cases\n"
        "<b>Time Remaining:</b> Calculating...\n\n"
        "<b>Contact:</b> @OguMarco",
        parse_mode=ParseMode.HTML
    )
    
    # Store message ID for future deletion
    user_last_messages[message.chat.id] = msg.message_id
    
    async def countdown():
        try:
            while True:
                remaining = int((end_time - datetime.now()).total_seconds())
                if remaining <= 0:
                    await msg.edit_text(
                        "<b>SESSION COMPLETED</b>\n\n"
                        "<b>Status:</b> Representative Offline\n"
                        "<b>Action:</b> Session Concluded\n\n"
                        "<b>Contact:</b> @OguMarco\n\n"
                        "<i>Use /time to start a new session</i>",
                        parse_mode=ParseMode.HTML
                    )
                    break
                time_left = format_time_left(remaining)
                await msg.edit_text(
                    "<b>ONLINE ACTIVE SESSION</b>\n\n"
                    "<b>Status:</b> Collecting Cases\n"
                    f"<b>Time Remaining:</b> {time_left}\n\n"
                    "<b>Contact:</b> @OguMarco",
                    parse_mode=ParseMode.HTML
                )
                await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error in countdown: {e}")
    
    asyncio.create_task(countdown())

# /sleep command
@dp.message(Command("sleep"))
async def sleep_command(message: Message):
    # Check if user is admin in groups
    if message.chat.type in ["group", "supergroup"] and not await is_user_admin(message):
        await message.answer("<b>ACCESS DENIED</b>\n\nOnly administrators can use this command.", parse_mode=ParseMode.HTML)
        return
    
    args = message.text.split()[1:]
    if not args:
        await message.answer(
            "<b>SLEEP MODE COMMAND USAGE</b>\n\n"
            "Format: <code>/sleep &lt;duration&gt;</code>\n"
            "Examples:\n"
            "• <code>/sleep 8</code> - 8 hours\n"
            "• <code>/sleep 7:30</code> - 7 hours 30 minutes\n\n"
            "<i>Sets a sleep mode timer</i>",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        delta = parse_time_arg(args[0])
    except ValueError as e:
        await message.answer(f"<b>ERROR</b>\n\n{e}", parse_mode=ParseMode.HTML)
        return

    # Delete previous bot message
    await delete_previous_message(message.chat.id)

    end_time = datetime.now() + delta
    
    msg = await message.reply(
        "<b>SLEEP MODE ACTIVATED</b>\n\n"
        "<b>Status:</b> Offline - Sleeping\n"
        "<b>Time Remaining:</b> Calculating...\n\n"
        "<b>Contact After:</b> @OguMarco",
        parse_mode=ParseMode.HTML
    )
    
    # Store message ID for future deletion
    user_last_messages[message.chat.id] = msg.message_id
    
    async def countdown():
        try:
            while True:
                remaining = int((end_time - datetime.now()).total_seconds())
                if remaining <= 0:
                    await msg.edit_text(
                        "<b>SLEEP MODE COMPLETED</b>\n\n"
                        "<b>Status:</b> Online - Active\n"
                        "<b>Action:</b> Ready To Collect Cases\n\n"
                        "<b>Contact:</b> @OguMarco",
                        parse_mode=ParseMode.HTML
                    )
                    break
                time_left = format_time_left(remaining)
                await msg.edit_text(
                    "<b>SLEEP MODE ACTIVE</b>\n\n"
                    "<b>Status:</b> Offline - Sleeping\n"
                    f"<b>Time Remaining:</b> {time_left}\n\n"
                    "<b>Contact After:</b> @OguMarco",
                    parse_mode=ParseMode.HTML
                )
                await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error in countdown: {e}")
    
    asyncio.create_task(countdown())

# Handle channel posts (commands sent in channels)
@dp.channel_post()
async def handle_channel_post(message: Message):
    if message.text and message.text.startswith('/'):
        command = message.text.split()[0][1:]
        
        # Delete previous bot message
        await delete_previous_message(message.chat.id)
        
        if command == "time":
            args = message.text.split()[1:]
            if not args:
                await message.answer(
                    "<b>TIME COMMAND USAGE</b>\n\n"
                    "Format: <code>/time &lt;duration&gt;</code>\n"
                    "Example: <code>/time 1:30</code>",
                    parse_mode=ParseMode.HTML
                )
                return

            try:
                delta = parse_time_arg(args[0])
            except ValueError as e:
                await message.answer(f"<b>ERROR</b>\n\n{e}", parse_mode=ParseMode.HTML)
                return

            end_time = datetime.now() + delta
            
            msg = await message.reply(
                "<b>ONLINE ACTIVE SESSION</b>\n\n"
                "<b>Status:</b> Collecting Cases\n"
                "<b>Time Remaining:</b> Calculating...\n\n"
                "<b>Contact:</b> @OguMarco",
                parse_mode=ParseMode.HTML
            )
            
            # Store message ID for future deletion
            user_last_messages[message.chat.id] = msg.message_id
            
            async def countdown():
                try:
                    while True:
                        remaining = int((end_time - datetime.now()).total_seconds())
                        if remaining <= 0:
                            await msg.edit_text(
                                "<b>SESSION COMPLETED</b>\n\n"
                                "<b>Status:</b> Representative Offline\n"
                                "<b>Action:</b> Session Concluded\n\n"
                                "<b>Contact:</b> @OguMarco",
                                parse_mode=ParseMode.HTML
                            )
                            break
                        time_left = format_time_left(remaining)
                        await msg.edit_text(
                            "<b>ONLINE ACTIVE SESSION</b>\n\n"
                            "<b>Status:</b> Collecting Cases\n"
                            f"<b>Time Remaining:</b> {time_left}\n\n"
                            "<b>Contact:</b> @OguMarco",
                            parse_mode=ParseMode.HTML
                        )
                        await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Error in countdown: {e}")
            
            asyncio.create_task(countdown())
        
        elif command == "sleep":
            args = message.text.split()[1:]
            if not args:
                await message.answer(
                    "<b>SLEEP MODE COMMAND USAGE</b>\n\n"
                    "Format: <code>/sleep &lt;duration&gt;</code>\n"
                    "Example: <code>/sleep 8</code>",
                    parse_mode=ParseMode.HTML
                )
                return

            try:
                delta = parse_time_arg(args[0])
            except ValueError as e:
                await message.answer(f"<b>ERROR</b>\n\n{e}", parse_mode=ParseMode.HTML)
                return

            end_time = datetime.now() + delta
            
            msg = await message.reply(
                "<b>SLEEP MODE ACTIVATED</b>\n\n"
                "<b>Status:</b> Offline - Sleeping\n"
                "<b>Time Remaining:</b> Calculating...\n\n"
                "<b>Contact After:</b> @OguMarco",
                parse_mode=ParseMode.HTML
            )
            
            # Store message ID for future deletion
            user_last_messages[message.chat.id] = msg.message_id
            
            async def countdown():
                try:
                    while True:
                        remaining = int((end_time - datetime.now()).total_seconds())
                        if remaining <= 0:
                            await msg.edit_text(
                                "<b>SLEEP MODE COMPLETED</b>\n\n"
                                "<b>Status:</b> Online - Active\n"
                                "<b>Action:</b> Ready To Collect Cases\n\n"
                                "<b>Contact:</b> @OguMarco",
                                parse_mode=ParseMode.HTML
                            )
                            break
                        time_left = format_time_left(remaining)
                        await msg.edit_text(
                            "<b>SLEEP MODE ACTIVE</b>\n\n"
                            "<b>Status:</b> Offline - Sleeping\n"
                            f"<b>Time Remaining:</b> {time_left}\n\n"
                            "<b>Contact After:</b> @OguMarco",
                            parse_mode=ParseMode.HTML
                        )
                        await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Error in countdown: {e}")
            
            asyncio.create_task(countdown())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Professional Timer Bot is starting...")
    print("Features:")
    print("- Bold formatted messages with paragraph style")
    print("- Automatic deletion of previous messages")
    print("- Reply to user messages")
    print("- Professional time display (01h 42min format)")
    print("- Contact information included")
    print("- Works in groups, private chats, and channels")
    asyncio.run(main())
