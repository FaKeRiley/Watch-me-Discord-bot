import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import random
import sqlite3
import os

class PfpPoster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Create the 'data' directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Connect to SQLite database in the data folder
        self.db = sqlite3.connect("data/pfp_and_banner.db")
        self.cursor = self.db.cursor()
        
        # Create table for PFP channels if it doesn't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pfp_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        ''')
        self.db.commit()
        
        # Starts the background loop
        self.pfp_loop.start()

    def cog_unload(self):
        # Safely stops the loop and closes the database connection
        self.pfp_loop.cancel()
        self.db.close()

    @app_commands.command(name="pfpsetup", description="Sets the channel for profile pictures (every 30 minutes).")
    @app_commands.checks.has_permissions(administrator=True)
    async def pfpsetup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """
        Allows an Administrator to set the channel. Saves it to the Database.
        """
        self.cursor.execute('''
            INSERT OR REPLACE INTO pfp_channels (guild_id, channel_id)
            VALUES (?, ?)
        ''', (interaction.guild.id, channel.id))
        self.db.commit()
        
        await interaction.response.send_message(f"✅ The PFP channel has been set to {channel.mention}! A new profile picture will be posted here every 30 minutes.")

    # The task that runs every 30 minutes
    @tasks.loop(minutes=30.0)
    async def pfp_loop(self):
        await self.bot.wait_until_ready()
        
        self.cursor.execute('SELECT guild_id, channel_id FROM pfp_channels')
        configs = self.cursor.fetchall()
        
        if not configs:
            return
            
        # Eine riesige, hochwertige Liste an Subreddits für die besten Discord-PFPs
        # Format: 'Interner_Name': ('Subreddit', 'Embed Titel')
        reddit_sources = {
            'discord_pfp': ('discordpfp', "🔥 Fire Discord PFP"),
            'anime_icons': ('animeicons', "🌸 Anime Icon"),
            'anime_pfp': ('AnimePFP', "✨ High Quality Anime PFP"),
            'street_anime': ('streetmoe', "🧢 Streetwear Anime PFP"),
            'cute_anime': ('awwnime', "💖 Cute Anime PFP"),
            'aesthetic': ('aesthetic', "✨ Aesthetic PFP"),
            'dark_grunge': ('grunge', "🦇 Dark / Grunge Aesthetic PFP"),
            'vaporwave': ('VaporwaveAesthetics', "💽 Vaporwave / Retro PFP"),
            'kpop': ('kpics', "🎤 K-Pop Idol PFP"),
            'cats': ('SupermodelCats', "🐱 Aesthetic Cat PFP"), # Viel besser als generische Katzen-APIs!
            'art': ('ImaginarySliceOfLife', "🎨 Beautiful Art PFP"),
            'gaming': ('gaming', "🎮 Gaming PFP")
        }
        
        # 'matching_pfp' wird als eigener Modus behandelt wegen der Galerie-Funktion
        categories = list(reddit_sources.keys()) + ['matching_pfp', 'matching_pfp'] # Matching 2x drin für höhere Wahrscheinlichkeit
        
        for guild_id, channel_id in configs:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                continue
                
            category = random.choice(categories)
            image_urls = [] 
            title = "🖼️ Your new profile picture!"
            
            try:
                async with aiohttp.ClientSession() as session:
                    
                    if category == 'matching_pfp':
                        # Spezielle Galerie-Logik für Matching PFPs über die native Reddit API
                        headers = {'User-Agent': 'Mozilla/5.0 DiscordBot PFP/2.0'}
                        async with session.get("https://www.reddit.com/r/MatchingPfps/random.json", headers=headers) as response:
                            if response.status == 200:
                                data = await response.json()
                                post = data[0]['data']['children'][0]['data']
                                
                                # Check if the post is a gallery (contains 2 or more images)
                                if post.get('is_gallery'):
                                    media = post.get('media_metadata', {})
                                    gallery_items = post.get('gallery_data', {}).get('items', [])
                                    for item in gallery_items:
                                        media_id = item.get('media_id')
                                        if media_id and media_id in media:
                                            m = media[media_id]
                                            if m.get('e') == 'Image':
                                                img_url = m['s']['u'].replace('&amp;', '&')
                                                image_urls.append(img_url)
                                else:
                                    # Fallback if the user stitched them into a single image
                                    img_url = post.get('url')
                                    if img_url and img_url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                                        image_urls.append(img_url)
                                
                                title = "💞 Matching PFP (Grab a friend!)"
                                
                        # Absolute fallback in case Reddit API limits us
                        if not image_urls:
                            async with session.get("https://meme-api.com/gimme/MatchingPfps") as fb_resp:
                                if fb_resp.status == 200:
                                    data = await fb_resp.json()
                                    url = data.get("url")
                                    if url: image_urls.append(url)
                                    title = "💞 Matching PFP (Grab a friend!)"

                    else:
                        # Für alle anderen Kategorien nutzen wir unser Dictionary und die Meme-API
                        subreddit, embed_title = reddit_sources[category]
                        title = embed_title
                        
                        async with session.get(f"https://meme-api.com/gimme/{subreddit}") as response:
                            if response.status == 200:
                                data = await response.json()
                                url = data.get("url")
                                if url: image_urls.append(url)

                # Senden der Bilder an den Channel
                if image_urls:
                    embeds = []
                    embed_color = discord.Color.random() # Gleiche Farbe für alle Bilder in einem Post
                    
                    # Wir limitieren es auf 4 Bilder (wichtig für Galerien), um Discord-Limits nicht zu sprengen
                    for i, url in enumerate(image_urls[:4]):
                        embed = discord.Embed(
                            title=title if i == 0 else None, # Titel nur beim ersten Bild
                            color=embed_color
                        )
                        embed.set_image(url=url)
                        
                        # Footer nur beim letzten Bild
                        if i == len(image_urls[:4]) - 1:
                            embed.set_footer(text="Click the image(s) to download and use them!")
                            
                        embeds.append(embed)
                        
                    # Discord erlaubt bis zu 10 Embeds in einer einzigen Nachricht
                    await channel.send(embeds=embeds)
                    
            except Exception as e:
                print(f"Error while fetching the PFP for Server {guild_id}: {e}")

async def setup(bot):
    await bot.add_cog(PfpPoster(bot))
