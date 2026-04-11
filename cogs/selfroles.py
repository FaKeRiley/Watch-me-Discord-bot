import discord
from discord.ext import commands
from discord import app_commands

# --- 1. Modal für Titel und Beschreibung ---
class TextModal(discord.ui.Modal, title="Setup Text"):
    def __init__(self, builder):
        super().__init__()
        self.builder = builder
        
        self.title_input = discord.ui.TextInput(
            label="Title",
            default=builder.panel_title,
            required=True,
            max_length=200
        )
        self.desc_input = discord.ui.TextInput(
            label="Description",
            style=discord.TextStyle.paragraph,
            default=builder.panel_desc,
            required=True,
            max_length=1000
        )
        self.add_item(self.title_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.builder.panel_title = self.title_input.value
        self.builder.panel_desc = self.desc_input.value
        await self.builder.update_menu(interaction)

# --- 2. Dynamisches Modal für die Emojis ---
class EmojiModal(discord.ui.Modal, title="Set Emojis for Roles"):
    def __init__(self, builder):
        super().__init__()
        self.builder = builder
        self.inputs = {}

        # Erstellt für jede ausgewählte Rolle ein Eingabefeld (Maximal 5)
        for role in builder.selected_roles:
            inp = discord.ui.TextInput(
                label=f"Emoji for: {role.name}"[:45], # Text auf 45 Zeichen limitieren
                default=builder.role_emojis.get(role.id, ""),
                required=False,
                max_length=50,
                placeholder="e.g. 🍎 or copied Discord Emoji"
            )
            self.inputs[role.id] = inp
            self.add_item(inp)

    async def on_submit(self, interaction: discord.Interaction):
        # Speichere die Emojis ab
        for role_id, text_input in self.inputs.items():
            val = text_input.value.strip()
            if val:
                self.builder.role_emojis[role_id] = val
            else:
                self.builder.role_emojis.pop(role_id, None) # Standard wiederherstellen, falls gelöscht
                
        await self.builder.update_menu(interaction)

# --- 3. Das interaktive Builder-Menü (Dashboard) ---
class RolePanelBuilder(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600) # Menü schließt sich nach 10 Minuten
        self.panel_title = "☑️ some roles"
        self.panel_desc = "get youre roles here"
        self.target_channel = None
        self.selected_roles = []
        self.role_emojis = {} # Speichert Emojis: {role_id: "emoji_string"}

    async def update_menu(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚙️ Reaction Roles Setup", description="Configure your new role message below.", color=discord.Color.dark_theme())
        
        embed.add_field(name="Title", value=self.panel_title, inline=False)
        embed.add_field(name="Description", value=self.panel_desc, inline=False)
        
        channel_text = self.target_channel.mention if self.target_channel else "🔴 `<Not Set>`"
        embed.add_field(name="Channel", value=channel_text, inline=False)
        
        if self.selected_roles:
            roles_text = ""
            for r in self.selected_roles:
                emoji = self.role_emojis.get(r.id, "🔘") # 🔘 ist der Standard
                roles_text += f"{emoji} ➔ {r.mention}\n"
        else:
            roles_text = "🔴 `<Not Set>`"
            
        embed.add_field(name="Roles", value=roles_text, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)

    # Zeile 1: Button für den Text
    @discord.ui.button(label="📝 Adjust Title & Desc", style=discord.ButtonStyle.primary, row=0)
    async def set_text(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TextModal(self))

    # Zeile 2: Dropdown für den Kanal
    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="📍 Select Target Channel", channel_types=[discord.ChannelType.text], row=1)
    async def select_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.target_channel = select.values[0]
        await self.update_menu(interaction)

    # Zeile 3: Dropdown für die Rollen (Maximal 5, weil Modals max 5 Eingabefelder haben dürfen)
    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="👥 Select Roles (Max 5)", min_values=1, max_values=5, row=2)
    async def select_roles(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.selected_roles = select.values
        await self.update_menu(interaction)

    # Zeile 4, Button 1: Emojis festlegen
    @discord.ui.button(label="🎨 Set Emojis", style=discord.ButtonStyle.secondary, row=3)
    async def set_emojis(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_roles:
            await interaction.response.send_message("❌ Please select some roles from the dropdown first!", ephemeral=True)
            return
        await interaction.response.send_modal(EmojiModal(self))

    # Zeile 4, Button 2: Abschicken
    @discord.ui.button(label="✅ Submit & Post Panel", style=discord.ButtonStyle.success, row=3)
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.target_channel:
            await interaction.response.send_message("❌ Please select a channel first!", ephemeral=True)
            return
        if not self.selected_roles:
            await interaction.response.send_message("❌ Please select at least one role!", ephemeral=True)
            return
        
        # FIX: Das echte Channel-Objekt laden, nicht das halbe AppCommandChannel-Objekt!
        real_channel = interaction.guild.get_channel(self.target_channel.id)
        if not real_channel:
            await interaction.response.send_message("❌ Could not find the real channel. Is it deleted?", ephemeral=True)
            return

        # Das finale Embed für den User-Kanal bauen
        final_view = discord.ui.View(timeout=None)
        embed_text = f"{self.panel_desc}\n\n**Options**\n"
        
        for role in self.selected_roles:
            emoji = self.role_emojis.get(role.id, "🔘")
            embed_text += f"{emoji} ➔ {role.mention}\n"
            
            # Button für die Rolle bauen
            btn = discord.ui.Button(label=role.name, style=discord.ButtonStyle.secondary, custom_id=f"role_{role.id}", emoji=emoji)
            final_view.add_item(btn)
            
        final_embed = discord.Embed(title=self.panel_title, description=embed_text, color=discord.Color.dark_theme())
        final_embed.set_footer(text="This message was written by the server staff")
        
        try:
            # Jetzt mit dem echten Channel-Objekt senden
            await real_channel.send(embed=final_embed, view=final_view)
            
            # Deaktiviere das Setup-Menü
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(content="✅ **Panel successfully published!**", view=self)
        except discord.HTTPException as e:
            # Falls ein Emoji ungültig ist, wirft Discord einen HTTP Fehler
            await interaction.response.send_message(f"❌ Error while sending. If you used custom emojis, make sure they are valid! Details: `{e}`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: Could not send message to {real_channel.mention}. Check my permissions! ({e})", ephemeral=True)


# --- 4. Der eigentliche Bot-Cog ---
class SelfRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Fängt die Klicks auf die fertigen Rollen-Buttons im Server ab
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get('custom_id', '')
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

    @app_commands.command(name="reactionroles", description="Opens the private Reaction Roles Builder menu.")
    @app_commands.default_permissions(administrator=True)
    async def rolepanel(self, interaction: discord.Interaction):
        builder = RolePanelBuilder()
        
        embed = discord.Embed(title="⚙️ Reaction Roles Setup", description="Configure your new role message below.", color=discord.Color.dark_theme())
        embed.add_field(name="Title", value=builder.panel_title, inline=False)
        embed.add_field(name="Description", value=builder.panel_desc, inline=False)
        embed.add_field(name="Channel", value="🔴 `<Not Set>`", inline=False)
        embed.add_field(name="Roles", value="🔴 `<Not Set>`", inline=False)
        
        await interaction.response.send_message(embed=embed, view=builder, ephemeral=True)

async def setup(bot):
    await bot.add_cog(SelfRoles(bot))
