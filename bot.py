import discord
from discord.ext import commands
import os
import asyncio

TOKEN = "Token_Here"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)  # Prefix wird hier ignoriert

async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

@bot.event
async def on_ready():
    print(f"✅ Bot gestartet als {bot.user}")
    # Globale Commands synchronisieren
    await bot.tree.sync()
    print("✅ Globale Slash Commands synchronisiert (kann bis zu 1 Stunde dauern)")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

asyncio.run(main())
