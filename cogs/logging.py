import discord
from discord.ext import commands
import sqlite3

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_log_channel_id(self, guild_id):
        db = sqlite3.connect("data/config.db")
        cursor = db.cursor()
        cursor.execute("SELECT log_channel_id FROM server_config WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        db.close()
        return result[0] if result and result[0] else None

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
            
        channel_id = self.get_log_channel_id(message.guild.id)
        if not channel_id: return
        
        log_channel = message.guild.get_channel(channel_id)
        if not log_channel: return

        embed = discord.Embed(title="🗑️ Message deleted", color=discord.Color.red())
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Content", value=message.content or "No text (e.g. Image)", inline=False)
        
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content:
            return

        channel_id = self.get_log_channel_id(before.guild.id)
        if not channel_id: return
        
        log_channel = before.guild.get_channel(channel_id)
        if not log_channel: return

        embed = discord.Embed(title="✏️ Message edited", color=discord.Color.yellow())
        embed.add_field(name="Author", value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Before", value=before.content, inline=False)
        embed.add_field(name="After", value=after.content, inline=False)
        embed.description = f"[Jump to message]({after.jump_url})"
        
        await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logging(bot))
