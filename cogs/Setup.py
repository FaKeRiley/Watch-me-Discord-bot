import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import re

class SetupModal(discord.ui.Modal, title='Configure Server Setup'):
    log_channel = discord.ui.TextInput(
        label='Log Channel ID',
        style=discord.TextStyle.short,
        placeholder='e.g. 123456789012345678',
        required=False
    )
    welcome_channel = discord.ui.TextInput(
        label='Welcome Channel ID',
        style=discord.TextStyle.short,
        placeholder='e.g. 123456789012345678',
        required=False
    )
    hub_channel = discord.ui.TextInput(
        label='Temp-Voice Hub Channel ID',
        style=discord.TextStyle.short,
        placeholder='e.g. 123456789012345678',
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        def parse_id(value):
            if not value: return None
            nums = re.sub(r'\D', '', value)
            return int(nums) if nums else None

        log_id = parse_id(self.log_channel.value)
        welcome_id = parse_id(self.welcome_channel.value)
        hub_id = parse_id(self.hub_channel.value)

        db = sqlite3.connect("data/config.db")
        cursor = db.cursor()
        
        cursor.execute("SELECT guild_id FROM server_config WHERE guild_id = ?", (interaction.guild_id,))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE server_config 
                SET log_channel_id = ?, welcome_channel_id = ?, hub_channel_id = ?
                WHERE guild_id = ?
            """, (log_id, welcome_id, hub_id, interaction.guild_id))
        else:
            cursor.execute("""
                INSERT INTO server_config (guild_id, log_channel_id, welcome_channel_id, hub_channel_id)
                VALUES (?, ?, ?, ?)
            """, (interaction.guild_id, log_id, welcome_id, hub_id))
        
        db.commit()
        db.close()

        await interaction.response.send_message("✅ Setup saved successfully! The channels have been updated.", ephemeral=True)

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⚙️ Start Setup", style=discord.ButtonStyle.primary, custom_id="start_setup")
    async def start_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You don't have permission for the setup.", ephemeral=True)
            return
        
        await interaction.response.send_modal(SetupModal())

class SetupCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(SetupView())
        
        db = sqlite3.connect("data/config.db")
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS server_config (
                guild_id INTEGER PRIMARY KEY,
                log_channel_id INTEGER,
                welcome_channel_id INTEGER,
                hub_channel_id INTEGER
            )
        """)
        db.commit()
        db.close()

    @app_commands.command(name="setup", description="Configure the bot's channels (Logs, Welcome, Temp-Voice).")
    @app_commands.default_permissions(administrator=True)
    async def setup_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛠️ Bot Setup",
            description="Click the button below to open the configuration window and enter the channel IDs.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, view=SetupView())

async def setup(bot):
    await bot.add_cog(SetupCommand(bot))
