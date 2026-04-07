import discord
from discord.ext import commands
from discord import app_commands

class SelfRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Dieser Listener fängt alle Button-Klicks des Bots ab
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
            
        custom_id = interaction.data.get("custom_id", "")
        if not custom_id.startswith("role_"):
            return

        role_id = int(custom_id.split("_")[1])
        role = interaction.guild.get_role(role_id)

        if not role:
            await interaction.response.send_message("❌ This role no longer exists.", ephemeral=True)
            return

        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message("❌ I don't have permission to manage this role.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"➖ The role {role.mention} has been removed.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"➕ You have received the role {role.mention}.", ephemeral=True)

    @app_commands.command(name="rolepanel", description="Creates a button panel for users to get roles.")
    @app_commands.describe(
        title="Title of the embed",
        role1="First role", role2="Second role (optional)", role3="Third role (optional)", role4="Fourth role (optional)"
    )
    @app_commands.default_permissions(administrator=True)
    async def rolepanel(self, interaction: discord.Interaction, title: str, role1: discord.Role, role2: discord.Role = None, role3: discord.Role = None, role4: discord.Role = None):
        embed = discord.Embed(title=title, description="Click the buttons below to get or remove the respective roles.", color=discord.Color.blurple())
        
        view = discord.ui.View(timeout=None)
        
        roles = [role1, role2, role3, role4]
        for role in roles:
            if role:
                # Wir speichern die Rollen-ID im Button, damit der Bot auch nach einem Neustart weiß, welche Rolle gemeint ist
                button = discord.ui.Button(label=role.name, style=discord.ButtonStyle.secondary, custom_id=f"role_{role.id}")
                view.add_item(button)

        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Role panel created successfully!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SelfRoles(bot))
