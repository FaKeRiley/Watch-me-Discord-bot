import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import random
import time
import math

# --- Pagination View for Crypto Logs ---
class CryptoLogView(discord.ui.View):
    def __init__(self, data, member_name):
        super().__init__(timeout=120)
        self.data = data
        self.member_name = member_name
        self.page = 0
        self.per_page = 6
        self.max_pages = max(1, math.ceil(len(data) / self.per_page))

    def create_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        current = self.data[start:end]
        
        embed = discord.Embed(
            title=f"📜 Crypto Logs: {self.member_name}", 
            description=f"📑 Page **{self.page + 1}** of **{self.max_pages}**",
            color=discord.Color.blue()
        )
        
        for l_type, coin, money, shares, ts in current:
            action = "📥 Bought" if l_type == "buy" else "📤 Sold"
            embed.add_field(
                name=f"{action} {coin}", 
                value=f"Shares: `{shares:.4f}`\nValue: `{money} 🪙`\n📅 <t:{ts}:R>", 
                inline=True
            )
            
        embed.set_footer(text="Use the buttons below to navigate.")
        return embed

    @discord.ui.button(label="⬅️ Back", style=discord.ButtonStyle.blurple, row=0)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0: 
            self.page -= 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.send_message("🛑 You are already on the first page!", ephemeral=True)

    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.blurple, row=0)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_pages - 1: 
            self.page += 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.send_message("🛑 You are already on the last page!", ephemeral=True)


class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sell_tax = 0.05  # 5% transaction fee when selling
        self.db = sqlite3.connect("data/economy.db")
        self.cursor = self.db.cursor()
        
        # Crypto Tables
        self.cursor.execute("CREATE TABLE IF NOT EXISTS crypto_market (name TEXT PRIMARY KEY, price REAL, emoji TEXT, last_price REAL DEFAULT 0.0)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS crypto_portfolio (user_id INTEGER, guild_id INTEGER, coin_name TEXT, amount REAL, PRIMARY KEY (user_id, guild_id, coin_name))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS crypto_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, guild_id INTEGER, type TEXT, coin TEXT, money INTEGER, shares REAL, timestamp INTEGER)")
        
        # Retrofit existing databases to add last_price if it's missing
        self.cursor.execute("PRAGMA table_info(crypto_market)")
        cols = [c[1] for c in self.cursor.fetchall()]
        if "last_price" not in cols:
            self.cursor.execute("ALTER TABLE crypto_market ADD COLUMN last_price REAL DEFAULT 0.0")
            self.cursor.execute("UPDATE crypto_market SET last_price = price")
        
        # Insert Default Coins if Market is empty
        self.cursor.execute("SELECT COUNT(*) FROM crypto_market")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.executemany("INSERT INTO crypto_market (name, price, emoji, last_price) VALUES (?, ?, ?, ?)", [
                ("Bitcoin", 50000.0, "🪙", 50000.0), 
                ("Ethereum", 3000.0, "💠", 3000.0), 
                ("Dogecoin", 0.20, "🐕", 0.20)
            ])
        self.db.commit()
        
        # Start the market fluctuation loop
        self.market_update.start()

    def cog_unload(self): 
        self.market_update.cancel()

    @tasks.loop(minutes=30)
    async def market_update(self):
        """Randomly changes crypto prices every 30 minutes."""
        self.cursor.execute("SELECT name, price FROM crypto_market")
        for name, price in self.cursor.fetchall():
            change = random.uniform(0.90, 1.10) # Fluctuates between -10% and +10%
            new_price = max(0.01, round(price * change, 4))
            # Save the old price and update with the new one
            self.cursor.execute("UPDATE crypto_market SET price = ?, last_price = ? WHERE name = ?", (new_price, price, name))
        self.db.commit()

    @market_update.before_loop
    async def before_market(self):
        await self.bot.wait_until_ready()

    crypto_group = app_commands.Group(name="crypto", description="📈 Invest your coins in the crypto market!")

    @crypto_group.command(name="market", description="📊 View live crypto prices and market trends.")
    async def crypto_market(self, interaction: discord.Interaction):
        self.cursor.execute("SELECT name, price, emoji, last_price FROM crypto_market")
        coins = self.cursor.fetchall()
        
        embed = discord.Embed(
            title="📈 Live Crypto Market", 
            description=f"⚠️ **Note:** A `{int(self.sell_tax*100)}%` transaction fee applies when selling.", 
            color=discord.Color.green()
        )
        
        for name, price, emoji, last_price in coins:
            # Determine the trend arrow and percentage change
            if last_price == 0.0 or price == last_price:
                trend = "➖ `0.00%`"
            elif price > last_price:
                percent_change = ((price - last_price) / last_price) * 100
                trend = f"🔼 `+{percent_change:.2f}%`"
            else:
                percent_change = ((last_price - price) / last_price) * 100
                trend = f"🔽 `-{percent_change:.2f}%`"
                
            embed.add_field(
                name=f"{emoji} {name} {trend}", 
                value=f"**{price:,.2f} 🪙**", 
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    @crypto_group.command(name="buy", description="📉 Invest a specific amount of coins into a crypto coin.")
    @app_commands.describe(coin="The name of the coin (e.g. Bitcoin)", investment="Amount of COINS you want to spend")
    async def crypto_buy(self, interaction: discord.Interaction, coin: str, investment: int):
        if investment <= 0: 
            return await interaction.response.send_message("🛑 ❌ Please enter a valid amount greater than 0.", ephemeral=True)
            
        self.cursor.execute("SELECT price, emoji, name FROM crypto_market WHERE name COLLATE NOCASE = ?", (coin,))
        res = self.cursor.fetchone()
        if not res: 
            return await interaction.response.send_message("🛑 ❌ Coin not found. Check `/crypto market`.", ephemeral=True)
        
        price, emoji, real_name = res
        shares = investment / price
        
        # Check user's bank balance
        self.cursor.execute("SELECT coins FROM bank WHERE user_id = ? AND guild_id = ?", (interaction.user.id, interaction.guild_id))
        bank_res = self.cursor.fetchone()
        user_coins = bank_res[0] if bank_res else 0
        
        if user_coins < investment: 
            return await interaction.response.send_message(f"💸 ❌ You don't have enough coins! You only have **{user_coins} 🪙**.", ephemeral=True)

        # Deduct coins
        self.cursor.execute("UPDATE bank SET coins = coins - ? WHERE user_id = ? AND guild_id = ?", (investment, interaction.user.id, interaction.guild_id))
        
        # Add shares to portfolio
        self.cursor.execute("INSERT INTO crypto_portfolio (user_id, guild_id, coin_name, amount) VALUES (?, ?, ?, ?) ON CONFLICT(user_id, guild_id, coin_name) DO UPDATE SET amount = amount + ?", (interaction.user.id, interaction.guild_id, real_name, shares, shares))
        
        # Add to logs
        self.cursor.execute("INSERT INTO crypto_logs (user_id, guild_id, type, coin, money, shares, timestamp) VALUES (?,?,?,?,?,?,?)", (interaction.user.id, interaction.guild_id, "buy", real_name, investment, shares, int(time.time())))
        
        self.db.commit()
        await interaction.response.send_message(f"📉 🎉 You successfully invested **{investment} 🪙** and received **{shares:.6f} {emoji} {real_name}**!")

    @crypto_group.command(name="sell", description="♻️ Sell your crypto (5% transaction fee applies).")
    @app_commands.describe(
        coin="The name of the coin to sell", 
        percentage="Sell a % of your holdings (1-100)", 
        amount="OR: Sell a specific amount of shares"
    )
    async def crypto_sell(self, interaction: discord.Interaction, coin: str, percentage: int = None, amount: float = None):
        if percentage is None and amount is None:
            return await interaction.response.send_message("🛑 ❌ Please specify either a `percentage` or an `amount` to sell.", ephemeral=True)
            
        self.cursor.execute("SELECT amount FROM crypto_portfolio WHERE user_id = ? AND guild_id = ? AND coin_name COLLATE NOCASE = ?", (interaction.user.id, interaction.guild_id, coin))
        port = self.cursor.fetchone()
        
        if not port or port[0] <= 0: 
            return await interaction.response.send_message("🛑 ❌ You do not own any of this coin.", ephemeral=True)
            
        port_amount = port[0]
        
        # Determine how many shares to sell
        if percentage is not None:
            sell_shares = port_amount * (min(max(percentage, 1), 100) / 100.0)
        else:
            if amount <= 0:
                return await interaction.response.send_message("🛑 ❌ Amount must be greater than 0.", ephemeral=True)
            sell_shares = min(amount, port_amount)
            
        self.cursor.execute("SELECT price, emoji, name FROM crypto_market WHERE name COLLATE NOCASE = ?", (coin,))
        price_res = self.cursor.fetchone()
        if not price_res:
            return await interaction.response.send_message("🛑 ❌ Coin no longer exists on the market.", ephemeral=True)
            
        price, emoji, real_name = price_res
        
        # Calculate money and tax
        gross_money = int(sell_shares * price)
        tax = int(gross_money * self.sell_tax)
        net_money = gross_money - tax
        
        # Deduct from portfolio
        if port_amount - sell_shares > 0.00001:
            self.cursor.execute("UPDATE crypto_portfolio SET amount = amount - ? WHERE user_id = ? AND guild_id = ? AND coin_name = ?", (sell_shares, interaction.user.id, interaction.guild_id, real_name))
        else:
            self.cursor.execute("DELETE FROM crypto_portfolio WHERE user_id = ? AND guild_id = ? AND coin_name = ?", (interaction.user.id, interaction.guild_id, real_name))
            
        # Add to logs
        self.cursor.execute("INSERT INTO crypto_logs (user_id, guild_id, type, coin, money, shares, timestamp) VALUES (?,?,?,?,?,?,?)", (interaction.user.id, interaction.guild_id, "sell", real_name, net_money, sell_shares, int(time.time())))
        
        # Add money to bank
        self.cursor.execute("UPDATE bank SET coins = coins + ? WHERE user_id = ? AND guild_id = ?", (net_money, interaction.user.id, interaction.guild_id))
        
        self.db.commit()
        await interaction.response.send_message(f"📈 🤝 You sold **{sell_shares:.4f} {emoji} {real_name}**.\n**Gross:** `{gross_money} 🪙`\n**Tax (-{int(self.sell_tax*100)}%):** `-{tax} 🪙`\n**Net Payout:** **{net_money} 🪙**")

    @crypto_group.command(name="portfolio", description="💼 View your crypto wallet and net worth.")
    async def crypto_portfolio(self, interaction: discord.Interaction):
        self.cursor.execute("SELECT coin_name, amount FROM crypto_portfolio WHERE user_id = ? AND guild_id = ?", (interaction.user.id, interaction.guild_id))
        holdings = self.cursor.fetchall()
        
        if not holdings: 
            return await interaction.response.send_message("📭 💼 Your crypto portfolio is empty. Use `/crypto buy` to start investing!", ephemeral=True)
            
        embed = discord.Embed(title=f"💼 {interaction.user.name}'s Portfolio", color=discord.Color.blue())
        total_gross = 0
        
        for c, a in holdings:
            if a <= 0.00001: continue
            self.cursor.execute("SELECT price, emoji FROM crypto_market WHERE name = ?", (c,))
            p_res = self.cursor.fetchone()
            if p_res:
                p, e = p_res
                val = int(a * p)
                total_gross += val
                embed.add_field(name=f"{e} {c}", value=f"Shares: `{a:.6f}`\nGross Value: `{val} 🪙`", inline=True)
                
        total_net = int(total_gross * (1 - self.sell_tax))
        embed.description = f"📊 **Total Gross Value:** `{total_gross} 🪙`\n💸 **Estimated Net Payout (after tax):** **{total_net} 🪙**"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="crypto_logs", description="🛡️ Admin: View the crypto transaction history of a member.")
    @app_commands.describe(member="The member to inspect", private="Should the response be hidden from others?")
    @app_commands.default_permissions(administrator=True)
    async def crypto_logs(self, interaction: discord.Interaction, member: discord.Member, private: bool = True):
        self.cursor.execute("SELECT type, coin, money, shares, timestamp FROM crypto_logs WHERE user_id = ? AND guild_id = ? ORDER BY timestamp DESC", (member.id, interaction.guild_id))
        logs = self.cursor.fetchall()
        
        if not logs: 
            return await interaction.response.send_message(f"📭 ❌ No transaction history found for {member.display_name}.", ephemeral=private)
            
        view = CryptoLogView(logs, member.display_name)
        await interaction.response.send_message(embed=view.create_embed(), view=view, ephemeral=private)

async def setup(bot):
    await bot.add_cog(Crypto(bot))
