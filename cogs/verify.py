import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class VerifyView(discord.ui.View):
    def __init__(self):
        # timeout=None ist wichtig, damit der Button auch nach einem Bot-Neustart noch funktioniert
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verify", style=discord.ButtonStyle.success, custom_id="verify_button")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Die Rolle aus der Datenbank abrufen
        db = sqlite3.connect("data/config.db")
        cursor = db.cursor()
        cursor.execute("SELECT verify_role_id FROM server_config WHERE guild_id = ?", (interaction.guild_id,))
        result = cursor.fetchone()
        db.close()

        # Überprüfen, ob eine Rolle in der DB existiert
        if not result or not result[0]:
            await interaction.response.send_message("❌ The verify role has not been set up properly. Please contact an admin.", ephemeral=True)
            return

        role = interaction.guild.get_role(result[0])
        if not role:
            await interaction.response.send_message("❌ The verify role no longer exists. Please contact an admin.", ephemeral=True)
            return

        # Überprüfen, ob der User die Rolle schon hat
        if role in interaction.user.roles:
            await interaction.response.send_message("✅ You are already verified!", ephemeral=True)
            return

        # Rolle vergeben
        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ You have been successfully verified! Welcome to the server.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to assign this role. An admin needs to move my bot role higher in the server settings!", ephemeral=True)

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(VerifyView()) # Macht den Button dauerhaft aktiv
        
        # Datenbank aktualisieren, um die Verify-Rolle zu speichern
        db = sqlite3.connect("data/config.db")
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS server_config (
                guild_id INTEGER PRIMARY KEY
            )
        """)
        
        cursor.execute("PRAGMA table_info(server_config)")
        columns = [col[1] for col in cursor.fetchall()]
        if "verify_role_id" not in columns:
            cursor.execute("ALTER TABLE server_config ADD COLUMN verify_role_id INTEGER")
            
        db.commit()
        db.close()

    @app_commands.command(name="verify", description="Setup the verification panel in this channel.")
    @app_commands.default_permissions(administrator=True)
    async def verify_cmd(self, interaction: discord.Interaction, role: discord.Role):
        # Überprüfen, ob der Bot die Rolle überhaupt vergeben darf
        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(f"❌ My highest role is lower than {role.mention}. I cannot assign it. Please drag my bot role above the verify role in the server settings.", ephemeral=True)
            return

        # Rolle in der Datenbank speichern
        db = sqlite3.connect("data/config.db")
        cursor = db.cursor()
        
        cursor.execute("SELECT guild_id FROM server_config WHERE guild_id = ?", (interaction.guild_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE server_config SET verify_role_id = ? WHERE guild_id = ?", (role.id, interaction.guild_id))
        else:
            cursor.execute("INSERT INTO server_config (guild_id, verify_role_id) VALUES (?, ?)", (interaction.guild_id, role.id))
            
        db.commit()
        db.close()

        # Das Embed erstellen
        embed = discord.Embed(
            title="🔒 Server Verification",
            description="Welcome to the server!\n\nTo gain access to all channels and prove you are human, please click the **Verify** button below.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Verification System")
        
        # Embed und Button in den Kanal senden
        await interaction.channel.send(embed=embed, view=VerifyView())
        
        # Dem Admin bestätigen (unsichtbar)
        await interaction.response.send_message("✅ Verification panel successfully created!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Verification(bot))
