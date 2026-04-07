import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class Counting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Datenbank für den aktuellen Zählerstand
        self.db = sqlite3.connect("data/counting.db")
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS counting (
                guild_id INTEGER PRIMARY KEY,
                current_number INTEGER,
                last_user_id INTEGER
            )
        """)
        self.db.commit()

        # Config-DB aktualisieren
        config_db = sqlite3.connect("data/config.db")
        c = config_db.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS server_config (guild_id INTEGER PRIMARY KEY)")
        c.execute("PRAGMA table_info(server_config)")
        columns = [col[1] for col in c.fetchall()]
        if "counting_channel_id" not in columns:
            c.execute("ALTER TABLE server_config ADD COLUMN counting_channel_id INTEGER")
        config_db.commit()
        config_db.close()

    @app_commands.command(name="setcounting", description="Set the channel for the counting game.")
    @app_commands.default_permissions(administrator=True)
    async def set_counting(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config_db = sqlite3.connect("data/config.db")
        c = config_db.cursor()
        c.execute("SELECT guild_id FROM server_config WHERE guild_id = ?", (interaction.guild_id,))
        if c.fetchone():
            c.execute("UPDATE server_config SET counting_channel_id = ? WHERE guild_id = ?", (channel.id, interaction.guild_id))
        else:
            c.execute("INSERT INTO server_config (guild_id, counting_channel_id) VALUES (?, ?)", (interaction.guild_id, channel.id))
        config_db.commit()
        config_db.close()
        
        # Setze den Zähler für diesen Server auf 0
        self.cursor.execute("REPLACE INTO counting (guild_id, current_number, last_user_id) VALUES (?, ?, ?)", (interaction.guild_id, 0, 0))
        self.db.commit()
        
        await interaction.response.send_message(f"✅ Counting channel set to {channel.mention}! Start counting from **1**.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        config_db = sqlite3.connect("data/config.db")
        c = config_db.cursor()
        c.execute("SELECT counting_channel_id FROM server_config WHERE guild_id = ?", (message.guild.id,))
        res = c.fetchone()
        config_db.close()

        if not res or not res[0] or message.channel.id != res[0]:
            return

        # Prüfe, ob die Nachricht überhaupt eine Zahl ist
        if not message.content.isdigit():
            return

        number = int(message.content)

        self.cursor.execute("SELECT current_number, last_user_id FROM counting WHERE guild_id = ?", (message.guild.id,))
        count_data = self.cursor.fetchone()
        
        if not count_data:
            current_number, last_user_id = 0, 0
        else:
            current_number, last_user_id = count_data

        # Regeln prüfen: Richtige Zahl? Anderer User?
        if number == current_number + 1 and message.author.id != last_user_id:
            await message.add_reaction("✅")
            self.cursor.execute("REPLACE INTO counting (guild_id, current_number, last_user_id) VALUES (?, ?, ?)", (message.guild.id, number, message.author.id))
            self.db.commit()
            
            # Bei besonderen Meilensteinen pinnen
            if number % 100 == 0:
                await message.pin()
                await message.channel.send(f"🎉 Wow! We reached **{number}**!")
        else:
            await message.add_reaction("❌")
            fail_reason = "You can't count twice in a row!" if message.author.id == last_user_id else f"Wrong number! Next number was **{current_number + 1}**."
            
            embed = discord.Embed(
                title="🚨 Ruined it!", 
                description=f"{message.author.mention} ruined the count at **{current_number}**.\n{fail_reason}\n\n**Start again from 1!**", 
                color=discord.Color.red()
            )
            await message.channel.send(embed=embed)
            
            # Zurücksetzen
            self.cursor.execute("REPLACE INTO counting (guild_id, current_number, last_user_id) VALUES (?, ?, ?)", (message.guild.id, 0, 0))
            self.db.commit()

async def setup(bot):
    await bot.add_cog(Counting(bot))
