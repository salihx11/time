import os
import discord
from discord import app_commands
from discord.ext import commands

# --- TOKEN CONFIGURATION ---
# Option 1: Load token from environment variable (recommended for production)
BOT_TOKEN = os.getenv("MTQxOTI4NDM1MjU4Nzc5NjU0MA.GbjXtp.kv1SLmZ7QpLVQI1fSKJim3Q5DJAjZDtp8_5A5o")

# Option 2: Load token from a file (for development)
if not BOT_TOKEN:
    try:
        with open("token.txt", "r") as token_file:
            BOT_TOKEN = token_file.read().strip()
    except FileNotFoundError:
        pass

# Option 3: Directly set token (least secure - only for testing)
if not BOT_TOKEN:
    # ⚠️ WARNING: Never commit this to version control with a real token
    # Replace with your actual token if using this method temporarily
    BOT_TOKEN = "MTQxOTI4NDM1MjU4Nzc5NjU0MA.GbjXtp.kv1SLmZ7QpLVQI1fSKJim3Q5DJAjZDtp8_5A5o"

if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise ValueError("""
❌ Bot token not found. 

You need to provide your bot token in one of these ways:
1. Set DISCORD_BOT_TOKEN environment variable
2. Create a token.txt file with your token
3. Replace YOUR_BOT_TOKEN_HERE with your actual token

Get your token from: https://discord.com/developers/applications/
""")

# --- INTENTS ---
intents = discord.Intents.default()
intents.message_content = True  # required if you want to use normal commands

# --- BOT ---
bot = commands.Bot(command_prefix="!", intents=intents)

# --- EVENT HANDLERS ---
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()  # sync slash commands globally
        print(f"✅ Logged in as {bot.user}. Synced {len(synced)} command(s).")
        print(f"✅ Bot is ready and running!")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    print(f"❌ Error in command {ctx.command}: {error}")

# --- SLASH COMMAND: /rep ---
@bot.tree.command(name="rep", description="Check if the representative is online")
async def rep(interaction: discord.Interaction):
    try:
        embed = discord.Embed(
            title="💼 Representative Status",
            description="🟢 Rep is online and currently taking cases.",
            color=0x00FF00
        )
        embed.set_footer(text="Please be patient; your case will be handled shortly.")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        print(f"❌ Error in /rep command: {e}")
        await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)

# --- OPTIONAL TEST COMMAND ---
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong! The bot is alive.")

# --- ERROR HANDLER FOR SLASH COMMANDS ---
@rep.error
async def rep_error(interaction: discord.Interaction, error):
    print(f"❌ Error in /rep command: {error}")
    await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)

# --- RUN BOT ---
if __name__ == "__main__":
    try:
        print("🤖 Starting bot...")
        bot.run(BOT_TOKEN)
    except discord.LoginFailure:
        print("❌ Failed to log in. Please check your bot token.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
