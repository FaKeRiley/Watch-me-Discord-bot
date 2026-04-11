import discord
from discord.ext import commands
import re
import asyncio

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Regex to catch standard web links
        self.url_regex = re.compile(r"(https?://\S+)")
        
        # Whitelisted domains that are allowed to be sent by normal users
        self.allowed_domains = [
            "tenor.com",
            "giphy.com",
            "imgur.com",
            "discord.com/attachments",
            "cdn.discordapp.com",
            "media.discordapp.net"
        ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages from bots or DMs
        if message.author.bot or not message.guild:
            return

        # Administrators bypass the filter entirely
        if message.author.guild_permissions.administrator:
            return

        content_lower = message.content.lower()
        violation = None

        # 1. Check for mass pings
        if "@everyone" in content_lower or "@here" in content_lower:
            violation = "mass pings (`@everyone` or `@here`)"
            
        # 2. Check for Discord invites specifically (catches discord.gg/xyz without https)
        elif "discord.gg/" in content_lower or "discord.com/invite/" in content_lower or "discordapp.com/invite/" in content_lower:
            violation = "Discord server invites"
            
        # 3. Check for unauthorized external links
        else:
            urls = self.url_regex.findall(message.content)
            if urls:
                for url in urls:
                    if not any(domain in url.lower() for domain in self.allowed_domains):
                        violation = "external links (only GIFs from Tenor/Giphy are allowed)"
                        break

        # If any violation is found, execute the AutoMod sequence
        if violation:
            try:
                # Delete the user's message
                await message.delete()
                
                # Send a warning
                warning_msg = await message.channel.send(
                    f"🛑 ❌ {message.author.mention}, you are not allowed to send {violation} here!"
                )
                
                # Delete the warning message after 5 seconds to keep chat clean
                await asyncio.sleep(5)
                await warning_msg.delete()
                
            except discord.Forbidden:
                # The bot does not have the "Manage Messages" permission
                print(f"Missing permissions to delete message from {message.author.name}")
            except discord.NotFound:
                # The message was already deleted
                pass

async def setup(bot):
    await bot.add_cog(AutoMod(bot))