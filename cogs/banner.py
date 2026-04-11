import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import random
import sqlite3
import os

class BannerPoster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Create the 'data' directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Connect to SQLite database in the data folder (uses the exact same file as pfp.py)
        self.db = sqlite3.connect("data/pfp_and_banner.db")
        self.cursor = self.db.cursor()
        
        # Create table for Banner channels if it doesn't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS banner_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        ''')
        self.db.commit()
        
        # Starts the background loop
        self.banner_loop.start()

    def cog_unload(self):
        # Safely stops the loop and closes the database connection
        self.banner_loop.cancel()
        self.db.close()

    @app_commands.command(name="bannersetup", description="Sets the channel for profile banners (every 30 minutes).")
    @app_commands.checks.has_permissions(administrator=True)
    async def bannersetup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """
        Allows an Administrator to set the banner channel. Saves it to the Database.
        """
        self.cursor.execute('''
            INSERT OR REPLACE INTO banner_channels (guild_id, channel_id)
            VALUES (?, ?)
        ''', (interaction.guild.id, channel.id))
        self.db.commit()
        
        await interaction.response.send_message(
            f"✅ The Banner channel has been set to {channel.mention}! "
            f"A new profile banner will be posted here every 30 minutes."
        )

    # The task that runs every 30 minutes
    @tasks.loop(minutes=30.0)
    async def banner_loop(self):
        await self.bot.wait_until_ready()
        
        self.cursor.execute('SELECT guild_id, channel_id FROM banner_channels')
        configs = self.cursor.fetchall()
        
        if not configs:
            return
            
        # Eine massive Liste an Subreddits, die perfekte Querformate für Discord Banner liefern
        # Format: 'Interner_Name': ('Subreddit', 'Embed Titel')
        reddit_sources = {
            'discord_banners': ('DiscordBanners', "🎨 Perfect Discord Banner"),
            'aesthetic': ('aestheticwallpapers', "✨ Aesthetic Banner"),
            'widescreen': ('WidescreenWallpaper', "🖥️ Ultra-Wide Aesthetic Banner"),
            'anime_landscape': ('Moescape', "🌸 Anime Landscape Banner"),
            'anime_backgrounds': ('BackgroundArt', "🖼️ Anime Background Art"),
            'fantasy_landscape': ('ImaginaryLandscapes', "🏰 Fantasy Landscape Banner"),
            'fantasy_city': ('ImaginaryCityscapes', "🏙️ Fantasy Cityscape Banner"),
            'pixel_art': ('PixelArt', "👾 Pixel Art Banner"),
            'cyberpunk': ('Cyberpunk', "🌃 Cyberpunk City Banner"),
            'synthwave': ('outrun', "🚗 Synthwave / Outrun Banner"),
            'vaporwave': ('VaporwaveAesthetics', "💽 Vaporwave / Retro Banner"),
            'nature': ('EarthPorn', "🌲 Beautiful Nature Banner"),
            'real_city': ('CityPorn', "🏙️ Real Cityscape Banner"),
            'space': ('SpacePorn', "🌌 Deep Space Banner"),
            'wallpapers': ('wallpapers', "🎮 High-Quality Wallpaper Banner")
        }
        
        categories = list(reddit_sources.keys())
        
        for guild_id, channel_id in configs:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                continue
                
            category = random.choice(categories)
            image_url = None
            
            try:
                async with aiohttp.ClientSession() as session:
                    # Wir nutzen unser Dictionary, um die URL und den Titel dynamisch zu generieren
                    subreddit, title = reddit_sources[category]
                    
                    async with session.get(f"https://meme-api.com/gimme/{subreddit}") as response:
                        if response.status == 200:
                            data = await response.json()
                            image_url = data.get("url")

                # Sende das Embed, wenn ein Bild erfolgreich abgerufen wurde
                if image_url:
                    embed = discord.Embed(title=title, color=discord.Color.random())
                    embed.set_image(url=image_url)
                    embed.set_footer(text="Click the image to download and use it as your banner!")
                    await channel.send(embed=embed)
                    
            except Exception as e:
                print(f"Error while fetching the Banner for Server {guild_id}: {e}")

async def setup(bot):
    await bot.add_cog(BannerPoster(bot))
