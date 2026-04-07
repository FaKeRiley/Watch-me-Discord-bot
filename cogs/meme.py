import discord
from discord.ext import commands
from discord import app_commands
import aiohttp

class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="meme", description="Gets a random meme from Reddit.")
    async def meme(self, interaction: discord.Interaction):
        # Zeige dem User an, dass der Bot "denkt", da der Download kurz dauern kann
        await interaction.response.defer()

        # Reddit Meme API aufrufen
        async with aiohttp.ClientSession() as session:
            async with session.get("https://meme-api.com/gimme") as response:
                if response.status != 200:
                    await interaction.followup.send("❌ Could not fetch a meme right now. Try again later!")
                    return
                
                data = await response.json()
                
                meme_url = data.get("url")
                meme_title = data.get("title")
                subreddit = data.get("subreddit")
                post_link = data.get("postLink")

                embed = discord.Embed(title=meme_title, url=post_link, color=discord.Color.random())
                embed.set_image(url=meme_url)
                embed.set_footer(text=f"From r/{subreddit}")

                await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Memes(bot))
