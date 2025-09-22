import discord
from discord import app_commands
from discord.ext import commands

# --- SETTINGS ---
BOT_TOKEN = "MTQxOTI4NDM1MjU4Nzc5NjU0MA.GdLERx.SVPW8hG08d2GisEeSj-4mLVDYCNTOIs8xm9mt8"

# --- INTENTS ---
intents = discord.Intents.default()
intents.message_content = True

# --- BOT ---
bot = commands.Bot(command_prefix="!", intents=intents)

# --- SYNC GLOBAL SLASH COMMANDS ---
@bot.event
async def on_ready():
    # Sync globally
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}. Slash commands synced globally.")

# --- GLOBAL SLASH COMMAND: /rep ---
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
bot.run(BOT_TOKEN)
