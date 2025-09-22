import discord
from discord import app_commands
from discord.ext import commands
import base64

# --- BOT TOKEN (Base64 Encoded) ---
# Encode your token once with:
#   python -c "import base64; print(base64.b64encode(b'your-token-here').decode())"
ENCODED_TOKEN = "TVRReE9USTRORE0xTWpVNE56YzVOalUwTUEuR2RMRVJ4LlNWUFc4aEcwOGQyR2lzRWVTai00bUxWRFlDTlRPSXM4eG05bXQ4"

# --- INTENTS ---
intents = discord.Intents.default()
intents.message_content = True

# --- BOT ---
bot = commands.Bot(command_prefix="!", intents=intents)

# --- SYNC GLOBAL SLASH COMMANDS ---
@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync globally
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
    BOT_TOKEN = base64.b64decode(ENCODED_TOKEN).decode()
    bot.run(BOT_TOKEN)
