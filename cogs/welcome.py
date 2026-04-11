import discord
from discord.ext import commands
import sqlite3

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_welcome_channel_id(self, guild_id):
        db = sqlite3.connect("data/config.db")
        cursor = db.cursor()
        cursor.execute("SELECT welcome_channel_id FROM server_config WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        db.close()
        return result[0] if result and result[0] else None

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel_id = self.get_welcome_channel_id(member.guild.id)
        if not channel_id: return
        
        channel = member.guild.get_channel(channel_id)
        if not channel: return

        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}! 🎉",
            description=f"Hey {member.mention}, glad to have you here! We are now **{member.guild.member_count}** members.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(content=member.mention, embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel_id = self.get_welcome_channel_id(member.guild.id)
        if not channel_id: return
        
        channel = member.guild.get_channel(channel_id)
        if not channel: return

        embed = discord.Embed(
            title="Goodbye! 👋",
            description=f"**{member.name}** left the server. Sad to see them go!",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
