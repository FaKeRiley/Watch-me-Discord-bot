import discord
from discord.ext import commands
import sqlite3

class TempVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = []

    def get_hub_channel_id(self, guild_id):
        db = sqlite3.connect("data/config.db")
        cursor = db.cursor()
        cursor.execute("SELECT hub_channel_id FROM server_config WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        db.close()
        return result[0] if result and result[0] else None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        hub_channel_id = self.get_hub_channel_id(member.guild.id)
        
        if after.channel and hub_channel_id and after.channel.id == hub_channel_id:
            category = after.channel.category
            
            new_channel = await member.guild.create_voice_channel(
                name=f"🔊 {member.name}'s Channel",
                category=category,
                user_limit=0
            )
            self.temp_channels.append(new_channel.id)
            
            try:
                await member.move_to(new_channel)
            except discord.HTTPException:
                await new_channel.delete()
                self.temp_channels.remove(new_channel.id)

        if before.channel and before.channel.id in self.temp_channels:
            if len(before.channel.members) == 0:
                await before.channel.delete()
                self.temp_channels.remove(before.channel.id)

async def setup(bot):
    await bot.add_cog(TempVoice(bot))
