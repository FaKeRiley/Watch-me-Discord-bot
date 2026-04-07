import discord
from discord.ext import commands
from discord import app_commands

class KickBanNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kicke ein Mitglied")
    @app_commands.describe(user="Mitglied auswählen", reason="Grund")
    @app_commands.checks.has_permissions(administrator=True)
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Kein Grund angegeben"):
        await user.kick(reason=reason)
        await interaction.response.send_message(f"👢 {user} wurde gekickt.\nGrund: `{reason}`")

    @app_commands.command(name="ban", description="Banne ein Mitglied")
    @app_commands.describe(user="Mitglied auswählen", reason="Grund")
    @app_commands.checks.has_permissions(administrator=True)
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Kein Grund angegeben"):
        await user.ban(reason=reason)
        await interaction.response.send_message(f"🔨 {user} wurde gebannt.\nGrund: `{reason}`")

    @app_commands.command(name="nuke", description="Löscht Nachrichten im aktuellen Channel")
    @app_commands.describe(anzahl="Anzahl der Nachrichten, die gelöscht werden sollen")
    @app_commands.checks.has_permissions(administrator=True)
    async def nuke(self, interaction: discord.Interaction, anzahl: int):
        if anzahl <= 0 or anzahl > 1000:
            await interaction.response.send_message("❌ Anzahl muss zwischen 1 und 1000 liegen.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = 0
        channel = interaction.channel
        while deleted < anzahl:
            to_delete = min(100, anzahl - deleted)
            messages = [m async for m in channel.history(limit=to_delete)]
            if not messages:
                break
            await channel.delete_messages(messages)
            deleted += len(messages)
        await interaction.followup.send(f"💣 `{deleted}` Nachrichten gelöscht.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(KickBanNuke(bot))
