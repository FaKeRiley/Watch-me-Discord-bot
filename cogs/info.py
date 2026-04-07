import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import datetime

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="🏓 Shows the bot's current latency.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! Latency: `{latency}ms`")

    @app_commands.command(name="userinfo", description="👤 Shows detailed information about a user.")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        
        embed = discord.Embed(title=f"👤 User Information - {member.name}", color=discord.Color.blue())
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=False)
        embed.add_field(name="📅 Account Created", value=discord.utils.format_dt(member.created_at, style="F"), inline=False)
        embed.add_field(name="📥 Joined Server", value=discord.utils.format_dt(member.joined_at, style="F"), inline=False)
        
        top_role = member.top_role.mention if member.top_role.name != "@everyone" else "None"
        embed.add_field(name="🎭 Highest Role", value=top_role, inline=False)

        # --- GLOBAL Birthday Fetch ---
        bday_str = "*Not set*"
        try:
            db = sqlite3.connect("data/birthdays.db")
            cursor = db.cursor()
            
            cursor.execute("PRAGMA table_info(birthdays)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Note: We now query ONLY by user_id and use LIMIT 1
            if "year" in columns:
                cursor.execute("SELECT day, month, year FROM birthdays WHERE user_id = ? LIMIT 1", (member.id,))
                result = cursor.fetchone()
                
                if result:
                    day, month, year = result
                    month_name = datetime.date(2000, month, 1).strftime('%B')
                    
                    if year:
                        today = datetime.date.today()
                        age = today.year - year - ((today.month, today.day) < (month, day))
                        bday_str = f"🎂 **{month_name} {day}, {year}** *(Age: {age})*"
                    else:
                        bday_str = f"🎂 **{month_name} {day}**"
            else:
                # Fallback for older databases
                cursor.execute("SELECT day, month FROM birthdays WHERE user_id = ? LIMIT 1", (member.id,))
                result = cursor.fetchone()
                if result:
                    day, month = result
                    month_name = datetime.date(2000, month, 1).strftime('%B')
                    bday_str = f"🎂 **{month_name} {day}**"

            db.close()
        except sqlite3.OperationalError:
            pass
            
        embed.add_field(name="🎈 Birthday", value=bday_str, inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Info(bot))
