import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import aiohttp

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="8ball", description="🎱 Ask the Magic 8-Ball a yes/no question.")
    @app_commands.describe(question="The question you want to ask")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes - definitely.",
            "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.",
            "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
            "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful."
        ]
        answer = random.choice(responses)
        
        embed = discord.Embed(title="🎱 Magic 8-Ball", color=discord.Color.dark_purple())
        embed.add_field(name="❓ Question:", value=question, inline=False)
        embed.add_field(name="🔮 Answer:", value=answer, inline=False)
        embed.set_footer(text=f"Asked by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ship", description="❤️ Calculate the love compatibility between two users.")
    @app_commands.describe(user1="First user", user2="Second user")
    async def ship(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
        seed = user1.id + user2.id
        random.seed(seed)
        percentage = random.randint(0, 100)
        random.seed()

        filled = round(percentage / 10)
        empty = 10 - filled
        progress_bar = f"[{'█' * filled}{'░' * empty}]"

        if percentage >= 90:
            status = "🔥 True Love! Get a room already!"
            color = discord.Color.brand_red()
        elif percentage >= 70:
            status = "💖 Looking very good! Cute couple."
            color = discord.Color.red()
        elif percentage >= 40:
            status = "🤝 Good friends! Maybe something more?"
            color = discord.Color.orange()
        elif percentage >= 20:
            status = "🤷 It's complicated. Keep trying."
            color = discord.Color.yellow()
        else:
            status = "💔 Absolutely no chance. Yikes."
            color = discord.Color.light_grey()

        embed = discord.Embed(title="💘 Matchmaking Calculator", description=f"Matching {user1.mention} and {user2.mention}", color=color)
        embed.add_field(name="Compatibility", value=f"**{percentage}%**\n`{progress_bar}`", inline=False)
        embed.add_field(name="Result", value=status, inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="hack", description="💻 Perform a highly advanced, totally real hack on a user.")
    @app_commands.describe(target="The user you want to 'hack'")
    async def hack(self, interaction: discord.Interaction, target: discord.Member):
        if target.id == self.bot.user.id:
            return await interaction.response.send_message("🛡️ Nice try, but my firewall is impenetrable!", ephemeral=True)
            
        await interaction.response.send_message(f"💻 `[INITIATING HACK SEQUENCE]` Target: **{target.name}**...")
        message = await interaction.original_response()

        passwords = ["ihovepuppies123", "password123", "qwertz", "mommy", "admin", "letmein99"]
        searches = ["how to get free nitro", "why is my dog built like a baked bean", "how to talk to girls", "cute cat pics", "is mayonnaise an instrument"]
        
        sequence = [
            f"🔍 `[FINDING IP ADDRESS]`... Found: `192.168.{random.randint(1,255)}.{random.randint(1,255)}`",
            f"🔓 `[BYPASSING DISCORD 2FA]`... Success!",
            f"📧 `[EXTRACTING EMAIL]`... `{target.name.lower()}{random.randint(10,99)}@gmail.com`",
            f"🔑 `[CRACKING PASSWORD]`... `{random.choice(passwords)}`",
            f"🌐 `[FETCHING SEARCH HISTORY]`... \"*{random.choice(searches)}*\"",
            f"📥 `[DOWNLOADING PRIVATE MEMES]`... [██████████] 100%",
            f"✅ `[HACK COMPLETE]` Data successfully sold to the dark web for 5 🪙."
        ]

        for step in sequence:
            await asyncio.sleep(1.5)
            await message.edit(content=step)

    @app_commands.command(name="choose", description="🤔 Let the bot choose between multiple options for you.")
    @app_commands.describe(options="Separate your choices with a comma (e.g. Pizza, Burger, Sushi)")
    async def choose(self, interaction: discord.Interaction, options: str):
        choices = [choice.strip() for choice in options.split(",") if choice.strip()]
        
        if len(choices) < 2:
            return await interaction.response.send_message("🛑 ❌ You need to give me at least two options separated by a comma!", ephemeral=True)
            
        chosen = random.choice(choices)
        
        embed = discord.Embed(title="🤔 The Bot Has Spoken", color=discord.Color.blue())
        embed.add_field(name="Options given:", value=", ".join(choices), inline=False)
        embed.add_field(name="I choose:", value=f"🎉 **{chosen}**", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slap", description="🖐️ Slap someone into the next dimension.")
    @app_commands.describe(target="The person who deserves a slap")
    async def slap(self, interaction: discord.Interaction, target: discord.Member):
        if target.id == interaction.user.id:
            return await interaction.response.send_message("🛑 ❌ You can't slap yourself, that's just sad.", ephemeral=True)
            
        if target.id == self.bot.user.id:
            return await interaction.response.send_message("🛡️ *Dodges the slap and slaps you back!* Don't touch the bot!", ephemeral=False)

        slaps = [
            f"🖐️ **{interaction.user.display_name}** slaps **{target.display_name}** right across the face!",
            f"🐟 **{interaction.user.display_name}** slaps **{target.display_name}** with a large, smelly trout!",
            f"💥 Ouch! **{interaction.user.display_name}** just slapped **{target.display_name}** into next week!",
            f"🗞️ **{interaction.user.display_name}** rolls up a newspaper and bonks **{target.display_name}** on the head."
        ]
        
        await interaction.response.send_message(random.choice(slaps))

    @app_commands.command(name="hug", description="🤗 Give someone a warm hug.")
    @app_commands.describe(target="The person who needs a hug")
    async def hug(self, interaction: discord.Interaction, target: discord.Member):
        if target.id == interaction.user.id:
            return await interaction.response.send_message("🫂 *The bot gives you a tight hug since you tried to hug yourself.*")

        hugs = [
            f"🤗 **{interaction.user.display_name}** gives **{target.display_name}** a big, warm hug!",
            f"🫂 **{interaction.user.display_name}** tackles **{target.display_name}** with a massive bear hug!",
            f"💖 **{interaction.user.display_name}** gently hugs **{target.display_name}**."
        ]
        
        await interaction.response.send_message(random.choice(hugs))

    @app_commands.command(name="iq", description="🧠 Scientifically calculate someone's IQ.")
    @app_commands.describe(target="The person to test (leave blank for yourself)")
    async def iq(self, interaction: discord.Interaction, target: discord.Member = None):
        member = target or interaction.user
        
        if member.id == self.bot.user.id:
            iq = 9999
        else:
            random.seed(member.id)
            iq = random.randint(10, 200)
            random.seed()

        if iq < 50:
            comment = "Maybe stick to eating crayons... 🖍️"
        elif iq < 90:
            comment = "Not the sharpest tool in the shed. 🔧"
        elif iq < 130:
            comment = "Pretty average, nothing to be ashamed of! 📊"
        elif iq < 180:
            comment = "Wow, we have a genius over here! 🎓"
        else:
            comment = "Absolute galaxy brain. You are terrifying. 🌌"

        embed = discord.Embed(title="🧠 IQ Test Results", color=discord.Color.fuchsia())
        embed.description = f"{member.mention}'s IQ is **{iq}**!\n\n*{comment}*"
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="🖼️ Get a user's profile picture in high resolution.")
    @app_commands.describe(target="The user whose avatar you want to see")
    async def avatar(self, interaction: discord.Interaction, target: discord.Member = None):
        member = target or interaction.user
        
        embed = discord.Embed(title=f"🖼️ Avatar of {member.display_name}", color=discord.Color.dark_theme())
        embed.set_image(url=member.display_avatar.url) 
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="redditmeme", description="😂 Fetch a random fresh meme from Reddit.")
    async def redditmeme(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://meme-api.com/gimme") as response:
                    if response.status == 200:
                        data = await response.json()
                        embed = discord.Embed(title=data["title"], url=data["postLink"], color=discord.Color.orange())
                        embed.set_image(url=data["url"])
                        embed.set_footer(text=f"👍 {data['ups']} | 💬 r/{data['subreddit']}")
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("🛑 ❌ Couldn't fetch a meme right now. Reddit might be napping!")
        except Exception as e:
            await interaction.followup.send(f"🛑 ❌ An error occurred while fetching the meme: `{e}`")

async def setup(bot):
    await bot.add_cog(Fun(bot))
