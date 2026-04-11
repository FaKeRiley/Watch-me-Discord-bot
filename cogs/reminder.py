import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import time

class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("data/reminders.db")
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id INTEGER,
                end_time INTEGER,
                reason TEXT
            )
        """)
        self.db.commit()
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    @app_commands.command(name="remind", description="Set a reminder.")
    @app_commands.describe(minutes="In how many minutes should I remind you?", reason="What should I remind you of?")
    async def remind(self, interaction: discord.Interaction, minutes: int, reason: str):
        if minutes <= 0:
            await interaction.response.send_message("❌ Time must be greater than 0 minutes.", ephemeral=True)
            return

        end_time = int(time.time()) + (minutes * 60)
        
        self.cursor.execute("INSERT INTO reminds (user_id, channel_id, end_time, reason) VALUES (?, ?, ?, ?)", 
                            (interaction.user.id, interaction.channel.id, end_time, reason))
        self.db.commit()

        await interaction.response.send_message(f"✅ Got it! I will remind you <t:{end_time}:R> about: `{reason}`")

    @tasks.loop(seconds=20)
    async def check_reminders(self):
        current_time = int(time.time())
        self.cursor.execute("SELECT id, user_id, channel_id, reason FROM reminds WHERE end_time <= ?", (current_time,))
        due_reminders = self.cursor.fetchall()

        for reminder in due_reminders:
            remind_id, user_id, channel_id, reason = reminder
            
            # Aus DB löschen
            self.cursor.execute("DELETE FROM reminds WHERE id = ?", (remind_id,))
            self.db.commit()

            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue
                
            user = self.bot.get_user(user_id)
            mention = user.mention if user else f"<@{user_id}>"

            embed = discord.Embed(title="⏰ Reminder!", description=f"You asked me to remind you:\n\n**{reason}**", color=discord.Color.blue())
            
            try:
                await channel.send(content=mention, embed=embed)
            except discord.Forbidden:
                pass # Falls der Bot im Kanal keine Schreibrechte mehr hat

    @check_reminders.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Reminders(bot))
