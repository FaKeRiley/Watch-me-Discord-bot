import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import time

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("data/afk.db")
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS afk_users (
                user_id INTEGER,
                guild_id INTEGER,
                reason TEXT,
                timestamp INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        self.db.commit()

    @app_commands.command(name="afk", description="Set your status to AFK (Away From Keyboard).")
    async def afk(self, interaction: discord.Interaction, reason: str = "AFK"):
        user_id = interaction.user.id
        guild_id = interaction.guild_id
        timestamp = int(time.time())

        self.cursor.execute("""
            INSERT OR REPLACE INTO afk_users (user_id, guild_id, reason, timestamp) 
            VALUES (?, ?, ?, ?)
        """, (user_id, guild_id, reason, timestamp))
        self.db.commit()

        await interaction.response.send_message(f"✅ I set your AFK status: `{reason}`")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        guild_id = message.guild.id

        # 1. Check if the author was AFK and has returned
        self.cursor.execute("SELECT reason FROM afk_users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        result = self.cursor.fetchone()
        
        if result:
            self.cursor.execute("DELETE FROM afk_users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
            self.db.commit()
            welcome_msg = await message.channel.send(f"👋 Welcome back {message.author.mention}, I removed your AFK status.")
            import asyncio
            await asyncio.sleep(5)
            await welcome_msg.delete() # Cleans up the chat

        # 2. Check if the author is pinging someone who is AFK
        for mentioned_user in message.mentions:
            self.cursor.execute("SELECT reason, timestamp FROM afk_users WHERE user_id = ? AND guild_id = ?", (mentioned_user.id, guild_id))
            ping_result = self.cursor.fetchone()
            
            if ping_result:
                reason = ping_result[0]
                timestamp = ping_result[1]
                await message.channel.send(f"💤 **{mentioned_user.name}** is currently AFK: `{reason}` *(since <t:{timestamp}:R>)*")

async def setup(bot):
    await bot.add_cog(AFK(bot))
