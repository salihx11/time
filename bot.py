import os
import discord
from discord import app_commands
from discord.ext import commands

# --- LOAD TOKEN FROM ENVIRONMENT ---
BOT_TOKEN = os.getenv("MTQxOTI4NDM1MjU4Nzc5NjU0MA.GdLERx.SVPW8hG08d2GisEeSj-4mLVDYCNTOIs8xm9mt8")
if not BOT_TOKEN:
    raise ValueError("❌ Bot token not found. Set DISCORD_BOT_TOKEN as an environment variable.")

# --- INTENTS ---
intents = discord.Intents.default()
intents.message_content = True  # required if you want to use normal commands

# --- BOT ---
bot = commands.Bot(command_prefix="!", intents=intents)

# --- SYNC GLOBAL SLASH COMMANDS ---
@bot.event
async def on_ready():
    await bot.tree.sync()  # sync slash commands globally
    print(f"✅ Logged in as {bot.user}. Slash commands synced globally.")

# --- SLASH COMMAND: /rep ---
@bot.tree.command(name="rep", description="Check if the representative is online")
async def rep(interaction: discord.Interaction):
    embed = discord.Embed(
        title="💼 Representative Status",
        description="🟢 Rep is online and currently taking cases.",
        color=0x00FF00
    )
    embed.set_footer(text="Please be patient; your case will be handled shortly.")
    await interaction.response.send_message(embed=embed)

# --- OPTIONAL TEST COMMAND ---
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong! The bot is alive.")

# --- RUN BOT ---
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
