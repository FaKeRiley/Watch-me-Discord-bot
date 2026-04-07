import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class Warns(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("data/warns.db")
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS warns (
                warn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                reason TEXT,
                moderator_id INTEGER
            )
        """)
        self.db.commit()

    @app_commands.command(name="warn", description="Warn a user (Staff only).")
    @app_commands.default_permissions(kick_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        self.cursor.execute("INSERT INTO warns (user_id, guild_id, reason, moderator_id) VALUES (?, ?, ?, ?)",
                            (member.id, interaction.guild_id, reason, interaction.user.id))
        self.db.commit()
        
        await interaction.response.send_message(f"⚠️ {member.mention} was warned by {interaction.user.mention}. Reason: `{reason}`")
        try:
            await member.send(f"You were warned in **{interaction.guild.name}**. Reason: `{reason}`")
        except discord.Forbidden:
            pass

    @app_commands.command(name="warns", description="Shows a user's warnings.")
    async def warns(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        
        self.cursor.execute("SELECT reason, moderator_id FROM warns WHERE user_id = ? AND guild_id = ?", (member.id, interaction.guild_id))
        warn_data = self.cursor.fetchall()
        
        if not warn_data:
            await interaction.response.send_message(f"✅ {member.mention} has no warnings.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Warnings for {member.name}", color=discord.Color.orange())
        embed.description = f"Total Warnings: **{len(warn_data)}**\n\n"
        
        for i, (reason, mod_id) in enumerate(warn_data, 1):
            embed.description += f"**{i}.** {reason} *(By: <@{mod_id}>)*\n"
            
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Warns(bot))
