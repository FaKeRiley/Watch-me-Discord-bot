import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio

# --- UI View for Would You Rather ---
class WYRView(discord.ui.View):
    def __init__(self, option1: str, option2: str):
        super().__init__(timeout=None)
        self.option1 = option1
        self.option2 = option2
        self.voted_users = set()

    @discord.ui.button(label="Option 1", style=discord.ButtonStyle.primary, custom_id="wyr_opt1")
    async def btn_option1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_vote(interaction, 1)

    @discord.ui.button(label="Option 2", style=discord.ButtonStyle.danger, custom_id="wyr_opt2")
    async def btn_option2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_vote(interaction, 2)

    async def handle_vote(self, interaction: discord.Interaction, choice: int):
        if interaction.user.id in self.voted_users:
            await interaction.response.send_message("You have already voted!", ephemeral=True)
            return
        
        self.voted_users.add(interaction.user.id)
        
        # Simulate worldwide statistics (random percentages that add up to 100)
        pct1 = random.randint(20, 80)
        pct2 = 100 - pct1
        
        embed = interaction.message.embeds[0]
        embed.clear_fields()
        embed.add_field(name=f"🔵 {self.option1}", value=f"**{pct1}%** of people chose this.", inline=False)
        embed.add_field(name=f"🔴 {self.option2}", value=f"**{pct2}%** of people chose this.", inline=False)
        
        # Update the message
        await interaction.response.edit_message(embed=embed)


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Word chain variables
        self.wordchain_channel_id = None
        self.last_word = None
        self.last_letter = None

        # Questions for Would You Rather
        self.wyr_questions = [
            ("Travel back in time", "Travel to the future"),
            ("Never listen to music again", "Never watch movies/shows again"),
            ("Be invisible", "Read minds"),
            ("Live in summer forever", "Live in winter forever"),
            ("Talk to animals", "Speak all languages fluently")
        ]

        # Questions for Trivia
        self.trivia_questions = [
            {"q": "What is the capital of Japan?", "a": ["tokyo"]},
            {"q": "What is the largest animal in the world?", "a": ["blue whale"]},
            {"q": "How many planets are in our solar system?", "a": ["8", "eight"]},
            {"q": "Which country does the game Minecraft come from?", "a": ["sweden"]},
            {"q": "Which element has the chemical symbol 'O'?", "a": ["oxygen"]}
        ]

    # --- Old Commands: Avatar ---
    @app_commands.command(name="avatar", description="See the avatar of a user")
    @app_commands.describe(target="The user whose avatar you want to see")
    async def avatar(self, interaction: discord.Interaction, target: discord.Member = None):
        member = target or interaction.user
        
        embed = discord.Embed(title=f"🖼️ Avatar of {member.display_name}", color=discord.Color.dark_theme())
        embed.set_image(url=member.display_avatar.url) 
        
        await interaction.response.send_message(embed=embed)

    # --- New Commands: Would You Rather ---
    @app_commands.command(name="wyr", description="Play 'Would You Rather...'!")
    async def wyr(self, interaction: discord.Interaction):
        q = random.choice(self.wyr_questions)
        
        embed = discord.Embed(title="🤔 Would you rather...", color=discord.Color.purple())
        embed.add_field(name="🔵 Option 1", value=q[0], inline=False)
        embed.add_field(name="🔴 Option 2", value=q[1], inline=False)
        
        view = WYRView(q[0], q[1])
        await interaction.response.send_message(embed=embed, view=view)

    # --- New Commands: Trivia ---
    @app_commands.command(name="trivia", description="Answer a tricky question and win!")
    async def trivia(self, interaction: discord.Interaction):
        q = random.choice(self.trivia_questions)
        
        embed = discord.Embed(
            title="🧠 Trivia Time!",
            description=f"**Question:** {q['q']}\n\n*You have 15 seconds! The first person to write the correct answer in the chat wins.*",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

        def check(m):
            # Checks if the message is in the same channel and not from a bot
            return m.channel == interaction.channel and not m.author.bot

        try:
            # Wait for a message in the chat
            while True:
                msg = await self.bot.wait_for('message', timeout=15.0, check=check)
                if msg.content.lower() in q['a']:
                    await msg.reply(f"🎉 **Correct!** {msg.author.mention} solved the question!")
                    break
        except asyncio.TimeoutError:
            await interaction.followup.send(f"⏰ **Time's up!** The correct answer was: `{q['a'][0].capitalize()}`")

    # --- New Commands: Word Chain Setup ---
    @app_commands.command(name="setup_wordchain", description="Set the channel for the word chain game.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setup_wordchain(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.wordchain_channel_id = channel.id
        self.last_word = None
        self.last_letter = None
        await interaction.response.send_message(f"✅ Word chain channel has been set to {channel.mention}! The game starts with any word.")

    # --- Word Chain Listener ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
            
        # Check if the message is in the designated word chain channel
        if self.wordchain_channel_id and message.channel.id == self.wordchain_channel_id:
            # Take only the first word of the message and convert to lowercase
            word = message.content.split()[0].lower()
            
            # Check if the word consists only of letters
            if not word.isalpha():
                return

            if self.last_word is None:
                # First word ever
                self.last_word = word
                self.last_letter = word[-1]
                await message.add_reaction("✅")
            else:
                # Check if the first letter matches the last letter of the previous word
                if word[0] == self.last_letter:
                    self.last_word = word
                    self.last_letter = word[-1]
                    await message.add_reaction("✅")
                else:
                    # Wrong word
                    await message.add_reaction("❌")
                    self.last_word = None
                    self.last_letter = None
                    await message.channel.send(f"❌ **Wrong!** {message.author.mention} broke the chain. The word should have started with **'{self.last_letter.upper()}'**!\n\n*The chain has been reset. Type any word to restart.*")

async def setup(bot):
    await bot.add_cog(Fun(bot))
