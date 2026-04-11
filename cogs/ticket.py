import discord
from discord.ext import commands
from discord import app_commands

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("The ticket will be deleted in 5 seconds...", ephemeral=True)
        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketOpenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Open Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        ticket_name = f"ticket-{interaction.user.name.lower()}"
        existing_channel = discord.utils.get(guild.channels, name=ticket_name)
        
        if existing_channel:
            await interaction.response.send_message(f"You already have an open ticket: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(name=ticket_name, overwrites=overwrites)
        
        await interaction.response.send_message(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)
        
        embed = discord.Embed(title="Ticket Support", description=f"Hello {interaction.user.mention}, a staff member will be with you shortly. Please describe your issue in the meantime.", color=discord.Color.green())
        await ticket_channel.send(content=f"{interaction.user.mention}", embed=embed, view=TicketCloseView())

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(TicketOpenView())
        self.bot.add_view(TicketCloseView())

    @app_commands.command(name="ticketpanel", description="Creates the ticket panel in the current channel.")
    @app_commands.default_permissions(administrator=True)
    async def ticketpanel(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Support Tickets", description="Click the button below to open a private support ticket.", color=discord.Color.blue())
        await interaction.channel.send(embed=embed, view=TicketOpenView())
        await interaction.response.send_message("Ticket panel sent successfully!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
