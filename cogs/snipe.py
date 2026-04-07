import discord
from discord.ext import commands
from discord import app_commands

class Snipe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Speichert die jeweils letzte gelöschte/bearbeitete Nachricht pro Kanal
        self.deleted_messages = {}
        self.edited_messages = {}

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        self.deleted_messages[message.channel.id] = message

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        self.edited_messages[before.channel.id] = (before, after)

    @app_commands.command(name="snipe", description="Snipes the last deleted message in this channel.")
    async def snipe(self, interaction: discord.Interaction):
        message = self.deleted_messages.get(interaction.channel_id)
        
        if not message:
            await interaction.response.send_message("❌ There is nothing to snipe here!", ephemeral=True)
            return

        embed = discord.Embed(description=message.content, color=discord.Color.red())
        embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
        embed.set_footer(text=f"Deleted in #{message.channel.name}")
        
        if message.attachments:
            embed.set_image(url=message.attachments[0].url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="editsnipe", description="Snipes the last edited message in this channel.")
    async def editsnipe(self, interaction: discord.Interaction):
        messages = self.edited_messages.get(interaction.channel_id)
        
        if not messages:
            await interaction.response.send_message("❌ There are no recently edited messages here!", ephemeral=True)
            return

        before, after = messages

        embed = discord.Embed(color=discord.Color.yellow())
        embed.set_author(name=before.author.name, icon_url=before.author.display_avatar.url)
        embed.add_field(name="Before", value=before.content, inline=False)
        embed.add_field(name="After", value=after.content, inline=False)
        embed.set_footer(text=f"Edited in #{before.channel.name}")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Snipe(bot))
