import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import sqlite3
import os
import time

class FreeGamesTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Create the 'data' directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Connect to SQLite database for free games
        self.db = sqlite3.connect("data/free_games.db")
        self.cursor = self.db.cursor()
        
        # Table for storing which server uses which channel
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS freegame_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        ''')
        
        # Table for storing already posted games with a timestamp
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS posted_games (
                game_id INTEGER PRIMARY KEY,
                post_time REAL
            )
        ''')
        
        # Falls die Tabelle aus der alten Version existiert, fügen wir die neue Spalte hinzu
        try:
            self.cursor.execute('ALTER TABLE posted_games ADD COLUMN post_time REAL')
        except sqlite3.OperationalError:
            pass # Spalte existiert bereits, alles gut!
            
        self.db.commit()
        
        # Start the background loop
        self.check_free_games.start()

    def cog_unload(self):
        # Safely stops the loop and closes the database connection
        self.check_free_games.cancel()
        self.db.close()

    @app_commands.command(name="freegames_setup", description="Sets the channel for free game alerts (Steam, Epic, GOG).")
    @app_commands.checks.has_permissions(administrator=True)
    async def freegames_setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """
        Allows an Administrator to set the channel. Saves it to the Database.
        """
        self.cursor.execute('''
            INSERT OR REPLACE INTO freegame_channels (guild_id, channel_id)
            VALUES (?, ?)
        ''', (interaction.guild.id, channel.id))
        self.db.commit()
        
        await interaction.response.send_message(
            f"✅ The Free Games alert channel has been set to {channel.mention}! "
            f"Whenever a new game is 100% free on Steam, Epic Games, or GOG, I will post it here."
        )

    # The task that runs every 1 hour to check for new free games
    @tasks.loop(hours=1.0)
    async def check_free_games(self):
        await self.bot.wait_until_ready()
        
        # 1. Datenbank-Pflege: Lösche alle Einträge, die älter als 30 Tage sind
        thirty_days_ago = time.time() - (30 * 24 * 60 * 60)
        self.cursor.execute('DELETE FROM posted_games WHERE post_time < ? OR post_time IS NULL', (thirty_days_ago,))
        self.db.commit()
        
        # Fetch all configured channels from the database
        self.cursor.execute('SELECT guild_id, channel_id FROM freegame_channels')
        configs = self.cursor.fetchall()
        
        if not configs:
            return # If no server has set this up, don't waste resources checking the API
            
        try:
            # Connect to GamerPower API (Aggregates free games from Epic, Steam, GOG, etc.)
            async with aiohttp.ClientSession() as session:
                url = "https://www.gamerpower.com/api/giveaways?type=game&platform=pc,steam,epic-games-store,gog"
                async with session.get(url) as response:
                    if response.status != 200:
                        return
                        
                    data = await response.json()
                    
                    # Check if DB is basically empty (first run)
                    self.cursor.execute('SELECT COUNT(*) FROM posted_games')
                    is_first_run = self.cursor.fetchone()[0] == 0
                    
                    games_to_post = []
                    current_time = time.time()
                    
                    for game in data:
                        game_id = game.get('id')
                        
                        # Check if we already posted this game
                        self.cursor.execute('SELECT 1 FROM posted_games WHERE game_id = ?', (game_id,))
                        if not self.cursor.fetchone():
                            # It's a new free game!
                            games_to_post.append(game)
                            # Mark as posted in the database with the current timestamp
                            self.cursor.execute('INSERT INTO posted_games (game_id, post_time) VALUES (?, ?)', (game_id, current_time))
                            
                    self.db.commit()
                    
                    # If this is the first run ever, limit to the 3 newest games to avoid spam
                    if is_first_run:
                        games_to_post = games_to_post[:3]
                        
                    # If there are no new games, just stop here
                    if not games_to_post:
                        return
                        
                    # Now send the new games to all configured channels
                    for guild_id, channel_id in configs:
                        channel = self.bot.get_channel(channel_id)
                        if channel is None:
                            continue
                            
                        for game in games_to_post:
                            # Extract game data
                            title = game.get('title', 'Unknown Title')
                            description = game.get('description', 'No description available.')
                            platforms = game.get('platforms', 'PC')
                            worth = game.get('worth', 'N/A')
                            image_url = game.get('image', '')
                            game_url = game.get('open_giveaway', '')
                            end_date = game.get('end_date', 'Unknown')
                            
                            # Create a beautiful embed
                            embed = discord.Embed(
                                title=f"🎁 FREE GAME: {title}",
                                description=f"**{title}** is currently 100% free!\n\n{description[:300]}...",
                                color=discord.Color.brand_green()
                            )
                            embed.add_field(name="💻 Platform", value=platforms, inline=True)
                            embed.add_field(name="💰 Original Price", value=f"~~{worth}~~ **(FREE)**", inline=True)
                            
                            if end_date != "N/A" and end_date != "Unknown":
                                embed.add_field(name="⏳ Ends At", value=end_date, inline=False)
                            else:
                                embed.add_field(name="⏳ Ends At", value="Hurry up, unknown end date!", inline=False)
                                
                            if image_url:
                                embed.set_image(url=image_url)
                                
                            embed.set_footer(text="Powered by GamerPower API • Claim it before it's gone!")
                            
                            # Add a clickable button linking to the game
                            view = discord.ui.View()
                            if game_url:
                                btn = discord.ui.Button(label="Claim Game Here", style=discord.ButtonStyle.link, url=game_url)
                                view.add_item(btn)
                                
                            try:
                                await channel.send(embed=embed, view=view)
                            except discord.Forbidden:
                                print(f"Missing permissions to send free games in channel {channel_id} (Guild: {guild_id})")
                                
        except Exception as e:
            print(f"Error checking for free games: {e}")

async def setup(bot):
    await bot.add_cog(FreeGamesTracker(bot))
