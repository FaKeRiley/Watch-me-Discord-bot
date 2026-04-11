import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Starboard Nachrichten DB
        self.db = sqlite3.connect("data/starboard.db")
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                original_id INTEGER PRIMARY KEY,
                starboard_msg_id INTEGER
            )
        """)
        self.db.commit()

        # Config DB aktualisieren (für den Kanal)
        config_db = sqlite3.connect("data/config.db")
        c = config_db.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS server_config (guild_id INTEGER PRIMARY KEY)")
        c.execute("PRAGMA table_info(server_config)")
        columns = [col[1] for col in c.fetchall()]
        if "starboard_channel_id" not in columns:
            c.execute("ALTER TABLE server_config ADD COLUMN starboard_channel_id INTEGER")
        config_db.commit()
        config_db.close()

    @app_commands.command(name="setstarboard", description="Set the channel for the Starboard.")
    @app_commands.default_permissions(administrator=True)
    async def set_starboard(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config_db = sqlite3.connect("data/config.db")
        c = config_db.cursor()
        c.execute("SELECT guild_id FROM server_config WHERE guild_id = ?", (interaction.guild_id,))
        if c.fetchone():
            c.execute("UPDATE server_config SET starboard_channel_id = ? WHERE guild_id = ?", (channel.id, interaction.guild_id))
        else:
            c.execute("INSERT INTO server_config (guild_id, starboard_channel_id) VALUES (?, ?)", (interaction.guild_id, channel.id))
        config_db.commit()
        config_db.close()
        
        await interaction.response.send_message(f"✅ Starboard channel set to {channel.mention}!", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if str(payload.emoji) != "⭐":
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return

        config_db = sqlite3.connect("data/config.db")
        c = config_db.cursor()
        c.execute("SELECT starboard_channel_id FROM server_config WHERE guild_id = ?", (payload.guild_id,))
        res = c.fetchone()
        config_db.close()

        if not res or not res[0]: return
        star_channel = guild.get_channel(res[0])
        if not star_channel: return

        channel = guild.get_channel(payload.channel_id)
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Zähle Sterne
        star_reaction = discord.utils.get(message.reactions, emoji="⭐")
        if not star_reaction or star_reaction.count < 3: # HIER kannst du einstellen, ab wie vielen Sternen es gepostet wird (aktuell 3)
            return

        embed = discord.Embed(description=message.content, color=discord.Color.gold())
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        
        if message.attachments:
            embed.set_image(url=message.attachments[0].url)
            
        embed.add_field(name="Original", value=f"[Jump to message]({message.jump_url})")

        star_text = f"⭐ **{star_reaction.count}** | {message.channel.mention}"

        self.cursor.execute("SELECT starboard_msg_id FROM messages WHERE original_id = ?", (message.id,))
        existing_msg_id = self.cursor.fetchone()

        if existing_msg_id:
            try:
                star_msg = await star_channel.fetch_message(existing_msg_id[0])
                await star_msg.edit(content=star_text, embed=embed)
            except discord.NotFound:
                pass
        else:
            star_msg = await star_channel.send(content=star_text, embed=embed)
            self.cursor.execute("INSERT INTO messages (original_id, starboard_msg_id) VALUES (?, ?)", (message.id, star_msg.id))
            self.db.commit()

async def setup(bot):
    await bot.add_cog(Starboard(bot))
