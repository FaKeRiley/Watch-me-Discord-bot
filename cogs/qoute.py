import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random

class Quotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("data/quotes.db")
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                quote_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                added_by INTEGER,
                content TEXT
            )
        """)
        self.db.commit()
        
        # Registriert das Kontext-Menü
        self.ctx_menu = app_commands.ContextMenu(
            name='Save Quote',
            callback=self.save_quote_context,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        # Entfernt das Kontext-Menü, falls das Cog entladen wird
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def save_quote_context(self, interaction: discord.Interaction, message: discord.Message):
        if not message.content:
            await interaction.response.send_message("❌ I can only save text messages as quotes.", ephemeral=True)
            return
            
        self.cursor.execute("INSERT INTO quotes (guild_id, user_id, added_by, content) VALUES (?, ?, ?, ?)", 
                            (interaction.guild_id, message.author.id, interaction.user.id, message.content))
        self.db.commit()
        
        await interaction.response.send_message(f"✅ Quote from {message.author.mention} saved successfully!", ephemeral=True)

    @app_commands.command(name="quote", description="Shows a random saved quote from the server.")
    async def get_quote(self, interaction: discord.Interaction):
        self.cursor.execute("SELECT user_id, content FROM quotes WHERE guild_id = ? ORDER BY RANDOM() LIMIT 1", (interaction.guild_id,))
        result = self.cursor.fetchone()
        
        if not result:
            await interaction.response.send_message("❌ No quotes saved on this server yet! Right-click a message -> Apps -> Save Quote to add one.", ephemeral=True)
            return
            
        user_id, content = result
        user = self.bot.get_user(user_id)
        username = user.name if user else "Unknown User"
        
        embed = discord.Embed(description=f'"{content}"', color=discord.Color.dark_theme())
        embed.set_footer(text=f"- {username}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Quotes(bot))
