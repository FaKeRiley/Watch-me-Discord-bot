import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import datetime

class Birthdays(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Database for Birthdays
        self.db = sqlite3.connect("data/birthdays.db")
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS birthdays (
                user_id INTEGER,
                guild_id INTEGER,
                day INTEGER,
                month INTEGER,
                year INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        
        # Check if 'year' column exists (for older databases)
        self.cursor.execute("PRAGMA table_info(birthdays)")
        columns = [col[1] for col in self.cursor.fetchall()]
        if "year" not in columns:
            self.cursor.execute("ALTER TABLE birthdays ADD COLUMN year INTEGER")
            
        self.db.commit()

        # Extend Config DB (for the birthday announcement channel per server)
        config_db = sqlite3.connect("data/config.db")
        c = config_db.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS server_config (guild_id INTEGER PRIMARY KEY)")
        c.execute("PRAGMA table_info(server_config)")
        columns = [col[1] for col in c.fetchall()]
        if "birthday_channel_id" not in columns:
            c.execute("ALTER TABLE server_config ADD COLUMN birthday_channel_id INTEGER")
        config_db.commit()
        config_db.close()

        # Start the daily check
        self.check_birthdays.start()

    def cog_unload(self):
        self.check_birthdays.cancel()

    birthday_group = app_commands.Group(name="birthday", description="🎂 Manage your global birthday.")

    @birthday_group.command(name="set", description="📅 Save your global birthday.")
    @app_commands.describe(
        day="Day of your birth (1-31)", 
        month="Month of your birth (1-12)",
        year="Year of your birth (Optional, e.g. 2005)"
    )
    async def set_birthday(self, interaction: discord.Interaction, day: int, month: int, year: int = None):
        if not (1 <= day <= 31) or not (1 <= month <= 12):
            return await interaction.response.send_message("🛑 ❌ Invalid date! Please provide a valid day (1-31) and month (1-12).", ephemeral=True)
            
        if year and (year < 1900 or year > datetime.date.today().year):
            return await interaction.response.send_message("🛑 ❌ Please provide a valid year (e.g., 2005).", ephemeral=True)

        # Delete any old per-server entries to enforce the new global system
        self.cursor.execute("DELETE FROM birthdays WHERE user_id = ?", (interaction.user.id,))
        
        # Save globally (using 0 as a placeholder for guild_id to fit the old schema)
        self.cursor.execute("INSERT INTO birthdays (user_id, guild_id, day, month, year) VALUES (?, 0, ?, ?, ?)", 
                            (interaction.user.id, day, month, year))
        self.db.commit()

        month_name = datetime.date(2000, month, 1).strftime('%B')
        year_str = f", {year}" if year else ""
        
        await interaction.response.send_message(f"🎉 ✅ Awesome! I saved your birthday globally as **{month_name} {day}{year_str}**.", ephemeral=True)

    @birthday_group.command(name="setchannel", description="⚙️ Admin: Set the channel for birthday wishes.")
    @app_commands.default_permissions(administrator=True)
    async def set_bday_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config_db = sqlite3.connect("data/config.db")
        c = config_db.cursor()
        c.execute("SELECT guild_id FROM server_config WHERE guild_id = ?", (interaction.guild_id,))
        if c.fetchone():
            c.execute("UPDATE server_config SET birthday_channel_id = ? WHERE guild_id = ?", (channel.id, interaction.guild_id))
        else:
            c.execute("INSERT INTO server_config (guild_id, birthday_channel_id) VALUES (?, ?)", (interaction.guild_id, channel.id))
        config_db.commit()
        config_db.close()
        
        await interaction.response.send_message(f"📢 ✅ Birthday announcements will now be sent to {channel.mention}!", ephemeral=True)

    @tasks.loop(hours=24)
    async def check_birthdays(self):
        today = datetime.datetime.today()
        current_day = today.day
        current_month = today.month
        current_year = today.year

        # Get all users who have a birthday today (DISTINCT prevents duplicates from old DB schemas)
        self.cursor.execute("SELECT DISTINCT user_id, year FROM birthdays WHERE day = ? AND month = ?", (current_day, current_month))
        birthday_users = self.cursor.fetchall()

        if not birthday_users:
            return

        config_db = sqlite3.connect("data/config.db")
        c = config_db.cursor()

        for user_id, year in birthday_users:
            # Check all servers the bot is currently in
            for guild in self.bot.guilds:
                member = guild.get_member(user_id)
                
                # If the birthday user is in this specific server, proceed
                if member:
                    c.execute("SELECT birthday_channel_id FROM server_config WHERE guild_id = ?", (guild.id,))
                    result = c.fetchone()
                    
                    if not result or not result[0]:
                        continue 
                        
                    channel = guild.get_channel(result[0])
                    if not channel: 
                        continue

                    # Calculate age if year was provided
                    age_text = ""
                    if year:
                        age = current_year - year
                        age_text = f"\nThey are turning **{age}** today! 🎈"

                    embed = discord.Embed(
                        title="🎉 Happy Birthday! 🎂",
                        description=f"Today is a special day! Let's all wish {member.mention} a fantastic birthday!{age_text}",
                        color=discord.Color.magenta()
                    )
                    embed.set_thumbnail(url=member.display_avatar.url)
                    
                    await channel.send(content=f"Hey {member.mention}, happy birthday! 🎈", embed=embed)
            
        config_db.close()

    @check_birthdays.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Birthdays(bot))
