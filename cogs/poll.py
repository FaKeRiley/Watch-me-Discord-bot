import discord
from discord.ext import commands
from discord import app_commands

class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="poll", description="Create a server poll.")
    @app_commands.describe(
        question="What is the poll about?",
        options="Separate options with a comma (e.g. Yes, No, Maybe) - Max 10 options."
    )
    @app_commands.default_permissions(manage_messages=True)
    async def poll_cmd(self, interaction: discord.Interaction, question: str, options: str):
        # Optionen an den Kommas trennen und Leerzeichen entfernen
        option_list = [opt.strip() for opt in options.split(",") if opt.strip()]
        
        if len(option_list) < 2:
            await interaction.response.send_message("❌ You need to provide at least 2 options separated by commas.", ephemeral=True)
            return
            
        if len(option_list) > 10:
            await interaction.response.send_message("❌ You can only provide up to 10 options.", ephemeral=True)
            return

        # Emoji-Zahlen von 1 bis 10
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        description = ""
        for i, option in enumerate(option_list):
            description += f"{emojis[i]} {option}\n\n"

        embed = discord.Embed(
            title=f"📊 {question}",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_author(name=f"Poll by {interaction.user.name}", icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message("✅ Poll created!", ephemeral=True)
        poll_msg = await interaction.channel.send(embed=embed)

        # Die Emojis zum Abstimmen hinzufügen
        for i in range(len(option_list)):
            await poll_msg.add_reaction(emojis[i])

async def setup(bot):
    await bot.add_cog(Poll(bot))
