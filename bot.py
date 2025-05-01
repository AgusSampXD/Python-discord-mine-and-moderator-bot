import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()

class ModBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.synced = False

    async def setup_hook(self):
        for ext in ["api.moderation", "api.welcome", "api.keuangan", "api.coin_system"]:
            await self.load_extension(ext)

        if not self.synced:
            await self.tree.sync()
            self.synced = True

bot = ModBot()

@bot.event
async def on_ready():
    print(f"Bot {bot.user} is online!")

    # Auto create folders
    os.makedirs("data", exist_ok=True)
    if not os.path.exists("data/transaksi.json") or os.path.getsize("data/transaksi.json") == 0:
        with open("data/transaksi.json", "w") as f:
            f.write('{"produk": {}, "pendapatan": 0, "pengeluaran": 0}')
    if not os.path.exists("data/testimoni.json") or os.path.getsize("data/testimoni.json") == 0:
        with open("data/testimoni.json", "w") as f:
            f.write("[]")

bot.run(TOKEN)