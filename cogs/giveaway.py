import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import time
import random

class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("data/giveaways.db")
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                message_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                guild_id INTEGER,
                end_time INTEGER,
                winners INTEGER,
                prize TEXT
            )
        """)
        self.db.commit()
        self.check_giveaways.start()

    def cog_unload(self):
        self.check_giveaways.cancel()

    @app_commands.command(name="giveaway", description="Start a new giveaway.")
    @app_commands.describe(duration_minutes="How many minutes should the giveaway last?", winners="Number of winners", prize="What is the prize?")
    @app_commands.default_permissions(manage_events=True)
    async def giveaway(self, interaction: discord.Interaction, duration_minutes: int, winners: int, prize: str):
        if duration_minutes <= 0 or winners <= 0:
            await interaction.response.send_message("❌ Duration and winners must be greater than 0.", ephemeral=True)
            return

        end_time = int(time.time()) + (duration_minutes * 60)
        
        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{end_time}:R>",
            color=discord.Color.purple()
        )
        embed.set_footer(text="React with 🎉 to enter!")

        await interaction.response.send_message("✅ Giveaway created!", ephemeral=True)
        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction("🎉")

        self.cursor.execute("INSERT INTO giveaways VALUES (?, ?, ?, ?, ?, ?)", 
                            (msg.id, interaction.channel.id, interaction.guild.id, end_time, winners, prize))
        self.db.commit()

    @tasks.loop(seconds=15)
    async def check_giveaways(self):
        current_time = int(time.time())
        self.cursor.execute("SELECT * FROM giveaways WHERE end_time <= ?", (current_time,))
        ended_giveaways = self.cursor.fetchall()

        for gw in ended_giveaways:
            msg_id, channel_id, guild_id, end_time, winners_count, prize = gw
            
            # Aus DB löschen
            self.cursor.execute("DELETE FROM giveaways WHERE message_id = ?", (msg_id,))
            self.db.commit()

            channel = self.bot.get_channel(channel_id)
            if not channel: continue
            
            try:
                msg = await channel.fetch_message(msg_id)
            except discord.NotFound:
                continue

            reaction = discord.utils.get(msg.reactions, emoji="🎉")
            if not reaction: continue

            users = [user async for user in reaction.users() if not user.bot]
            
            if len(users) == 0:
                await channel.send(f"No one entered the giveaway for **{prize}**.")
                continue

            # Gewinner ziehen
            actual_winners = min(winners_count, len(users))
            winners_list = random.sample(users, actual_winners)
            winners_mentions = ", ".join([w.mention for w in winners_list])

            # Embed updaten
            ended_embed = msg.embeds[0]
            ended_embed.description = f"**Prize:** {prize}\n**Winners:** {winners_mentions}\n**Ended:** <t:{end_time}:R>"
            ended_embed.color = discord.Color.default()
            ended_embed.set_footer(text="Giveaway ended!")
            await msg.edit(embed=ended_embed)

            await channel.send(f"🎉 Congratulations {winners_mentions}! You won **{prize}**!")

    @check_giveaways.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Giveaways(bot))
