import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random

class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("data/levels.db")
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                guild_id INTEGER,
                xp INTEGER,
                level INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        self.db.commit()

    def get_level_channel_id(self, guild_id):
        try:
            db = sqlite3.connect("data/config.db")
            cursor = db.cursor()
            cursor.execute("SELECT level_channel_id FROM server_config WHERE guild_id = ?", (guild_id,))
            result = cursor.fetchone()
            db.close()
            return result[0] if result and result[0] else None
        except Exception:
            return None

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        guild_id = message.guild.id

        self.cursor.execute("SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        result = self.cursor.fetchone()

        xp_to_add = random.randint(15, 25)

        if result is None:
            self.cursor.execute("INSERT INTO users (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)", (user_id, guild_id, xp_to_add, 0))
        else:
            current_xp = result[0] + xp_to_add
            current_level = result[1]
            
            xp_needed = (current_level + 1) * 100

            if current_xp >= xp_needed:
                current_level += 1
                current_xp = 0 
                
                # --- NEU: Münzen für Level Up geben ---
                coin_reward = current_level * 100  # Formel: Level * 100 (z.B. Level 5 = 500 Coins)
                try:
                    eco_db = sqlite3.connect("data/economy.db")
                    eco_cursor = eco_db.cursor()
                    
                    # Spalte last_work prüfen/hinzufügen (für Kompatibilität mit dem neuen Economy Cog)
                    eco_cursor.execute("PRAGMA table_info(bank)")
                    columns = [col[1] for col in eco_cursor.fetchall()]
                    if "last_work" not in columns:
                        eco_cursor.execute("ALTER TABLE bank ADD COLUMN last_work INTEGER DEFAULT 0")
                        
                    eco_cursor.execute("SELECT coins FROM bank WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
                    eco_res = eco_cursor.fetchone()
                    if eco_res:
                        eco_cursor.execute("UPDATE bank SET coins = ? WHERE user_id = ? AND guild_id = ?", (eco_res[0] + coin_reward, user_id, guild_id))
                    else:
                        eco_cursor.execute("INSERT INTO bank (user_id, guild_id, coins, last_daily, last_work) VALUES (?, ?, ?, ?, ?)", (user_id, guild_id, coin_reward, "", 0))
                    eco_db.commit()
                    eco_db.close()
                    coin_msg = f"\n💰 You also received a reward of **{coin_reward} 🪙**!"
                except Exception as e:
                    print("Fehler beim Hinzufügen der Level-Coins:", e)
                    coin_msg = ""
                # --------------------------------------

                lvl_msg = f"🎉 Congratulations {message.author.mention}, you reached level **{current_level}**!{coin_msg}"
                
                channel_id = self.get_level_channel_id(guild_id)
                if channel_id:
                    lvl_channel = message.guild.get_channel(channel_id)
                    if lvl_channel:
                        await lvl_channel.send(lvl_msg)
                    else:
                        await message.channel.send(lvl_msg) 
                else:
                    await message.channel.send(lvl_msg) 

            self.cursor.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?", (current_xp, current_level, user_id, guild_id))
            
        self.db.commit()

    @app_commands.command(name="rank", description="Shows your current level.")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        
        self.cursor.execute("SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?", (member.id, interaction.guild_id))
        result = self.cursor.fetchone()

        if result is None:
            await interaction.response.send_message(f"❌ {member.mention} hasn't sent any messages yet.", ephemeral=True)
            return

        current_xp = result[0]
        current_level = result[1]
        xp_needed = (current_level + 1) * 100

        embed = discord.Embed(title=f"Rank of {member.name}", color=discord.Color.purple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Level", value=f"**{current_level}**", inline=True)
        embed.add_field(name="XP", value=f"**{current_xp} / {xp_needed}**", inline=True)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Level(bot))
