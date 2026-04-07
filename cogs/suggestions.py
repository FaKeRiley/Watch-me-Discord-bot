import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Stellt sicher, dass die Datenbank bereit ist und fügt die neue Spalte hinzu, falls sie fehlt
        db = sqlite3.connect("data/config.db")
        cursor = db.cursor()
        
        # Erstellt die Tabelle, falls sie noch gar nicht existiert
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS server_config (
                guild_id INTEGER PRIMARY KEY
            )
        """)
        
        # Prüft, ob die Spalte 'suggestion_channel_id' existiert, und fügt sie hinzu
        cursor.execute("PRAGMA table_info(server_config)")
        columns = [col[1] for col in cursor.fetchall()]
        if "suggestion_channel_id" not in columns:
            cursor.execute("ALTER TABLE server_config ADD COLUMN suggestion_channel_id INTEGER")
            
        db.commit()
        db.close()

    @app_commands.command(name="setsuggestchannel", description="Set the channel where suggestions should be posted.")
    @app_commands.default_permissions(administrator=True)
    async def set_suggest_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Erlaubt Admins, den Vorschlags-Kanal festzulegen."""
        db = sqlite3.connect("data/config.db")
        cursor = db.cursor()
        
        cursor.execute("SELECT guild_id FROM server_config WHERE guild_id = ?", (interaction.guild_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE server_config SET suggestion_channel_id = ? WHERE guild_id = ?", (channel.id, interaction.guild_id))
        else:
            cursor.execute("INSERT INTO server_config (guild_id, suggestion_channel_id) VALUES (?, ?)", (interaction.guild_id, channel.id))
            
        db.commit()
        db.close()
        
        await interaction.response.send_message(f"✅ Suggestion channel successfully set to {channel.mention}!", ephemeral=True)

    @app_commands.command(name="suggest", description="Submit a suggestion for the server.")
    async def suggest(self, interaction: discord.Interaction, suggestion: str):
        """Erlaubt Usern, einen Vorschlag einzureichen."""
        # Kanal-ID aus der Datenbank abrufen
        db = sqlite3.connect("data/config.db")
        cursor = db.cursor()
        cursor.execute("SELECT suggestion_channel_id FROM server_config WHERE guild_id = ?", (interaction.guild_id,))
        result = cursor.fetchone()
        db.close()

        if not result or not result[0]:
            await interaction.response.send_message("❌ The suggestion channel has not been set up yet. Ask an admin to use `/setsuggestchannel`.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(result[0])
        if not channel:
            await interaction.response.send_message("❌ The configured suggestion channel could not be found.", ephemeral=True)
            return

        # Embed erstellen
        embed = discord.Embed(
            title="💡 New Suggestion", 
            description=suggestion, 
            color=discord.Color.gold()
        )
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"User ID: {interaction.user.id}")

        # Dem User antworten (nur er sieht diese Bestätigung)
        await interaction.response.send_message("✅ Your suggestion has been successfully submitted!", ephemeral=True)
        
        # Den Vorschlag in den Kanal posten und Reaktionen hinzufügen
        msg = await channel.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

async def setup(bot):
    await bot.add_cog(Suggestions(bot))
