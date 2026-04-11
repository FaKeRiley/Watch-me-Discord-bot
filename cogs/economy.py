import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import datetime
import random
import time
import math

# --- Pagination View for the Shop ---
class ShopView(discord.ui.View):
    def __init__(self, data):
        super().__init__(timeout=120)
        self.data = data
        self.page = 0
        # Dynamic items per page: 4 if few items, 6 if more items
        self.per_page = 6 if len(data) > 8 else 4  
        self.max_pages = max(1, math.ceil(len(data) / self.per_page))

    def create_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        current_items = self.data[start:end]
        
        embed = discord.Embed(
            title="🛒 Daily Shop", 
            description=f"✨ New items every 24h! Use `/buy [Name]` to purchase.\n\n📑 Page **{self.page + 1}** of **{self.max_pages}**",
            color=discord.Color.teal()
        )
        
        for name, price, rarity, emoji, weight in current_items:
            embed.add_field(
                name=f"{emoji} {name}",
                value=f"💳 Price: **{price} 🪙**\n🌟 Rarity: `{rarity}`",
                inline=False
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


# --- Pagination View for the Catalog ---
class CatalogView(discord.ui.View):
    def __init__(self, cog, guild_id, guild_name, private):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id
        self.guild_name = guild_name
        self.private = private
        self.page = 0
        self.update_data()
        
        if self.private:
            self.toggle_btn = discord.ui.Button(
                label="Toggle Default Items", 
                style=discord.ButtonStyle.danger if not self.disabled_defaults else discord.ButtonStyle.success, 
                row=1, 
                emoji="⚙️"
            )
            self.toggle_btn.callback = self.toggle_defaults
            self.add_item(self.toggle_btn)

    def update_data(self):
        self.disabled_defaults = self.cog.are_defaults_disabled(self.guild_id)
        if self.disabled_defaults:
            self.cog.cursor.execute("SELECT name, price, rarity, emoji, item_type FROM server_shop_catalog WHERE guild_id = ? AND is_default = 0", (self.guild_id,))
        else:
            self.cog.cursor.execute("SELECT name, price, rarity, emoji, item_type FROM server_shop_catalog WHERE guild_id = ?", (self.guild_id,))
        
        self.data = self.cog.cursor.fetchall()
        # Dynamic items per page
        self.per_page = 6 if len(self.data) > 8 else 4
        self.max_pages = max(1, math.ceil(len(self.data) / self.per_page))
        if self.page >= self.max_pages: 
            self.page = max(0, self.max_pages - 1)

    def create_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        current_items = self.data[start:end]
        
        status_text = "🔴 *Default items are disabled*" if self.disabled_defaults else "🟢 *All items active*"
        
        embed = discord.Embed(
            title=f"📜 Server Catalog - {self.guild_name}", 
            description=f"{status_text}\n\n📑 Page **{self.page + 1}** of **{self.max_pages}**",
            color=discord.Color.gold()
        )
        
        if not current_items:
            embed.add_field(name="📭 Empty", value="There are currently no items here.", inline=False)
            
        for name, price, rarity, emoji, item_type in current_items:
            embed.add_field(
                name=f"{emoji} {name}",
                value=f"💳 Price: `{price} 🪙`\n✨ Rarity: `{rarity}`\n🏷️ Type: `{item_type}`",
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

    async def toggle_defaults(self, interaction: discord.Interaction):
        new_val = 0 if self.disabled_defaults else 1
        self.cog.cursor.execute("INSERT INTO eco_settings (guild_id, disable_defaults) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET disable_defaults = ?", (self.guild_id, new_val, new_val))
        self.cog.db.commit()
        
        self.update_data()
        self.toggle_btn.style = discord.ButtonStyle.danger if not self.disabled_defaults else discord.ButtonStyle.success
        
        await interaction.response.edit_message(embed=self.create_embed(), view=self)


# --- Modal for Adding Items ---
class AddItemModal(discord.ui.Modal):
    item_name = discord.ui.TextInput(label='🏷️ Item Name', placeholder='e.g. VIP Package', style=discord.TextStyle.short, required=True, max_length=50)
    item_price = discord.ui.TextInput(label='💳 Price (Coins)', placeholder='e.g. 1000', style=discord.TextStyle.short, required=True)
    item_emoji = discord.ui.TextInput(label='✨ Emoji', placeholder='e.g. ⭐', style=discord.TextStyle.short, required=True, max_length=10)
    item_weight = discord.ui.TextInput(label='⚖️ Spawn Weight (1-100)', placeholder='Frequency in shop', style=discord.TextStyle.short, required=True)

    def __init__(self, rarity: str, item_type: str):
        super().__init__(title='📦 Add New Shop Item')
        self.rarity, self.item_type = rarity, item_type
        if self.item_type == "dm":
            self.msg = discord.ui.TextInput(label='📨 DM Message', style=discord.TextStyle.paragraph, required=True)
        elif self.item_type == "item":
            self.msg = discord.ui.TextInput(label='⚡ Usage Message', placeholder='{user} uses {item}!', style=discord.TextStyle.paragraph, required=True)
        else:
            self.msg = discord.ui.TextInput(label='🎭 Discord Role Name', placeholder='VIP', style=discord.TextStyle.short, required=True)
        self.add_item(self.msg)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            p, w = int(self.item_price.value), int(self.item_weight.value)
            dm, use, role = (self.msg.value if self.item_type == t else None for t in ["dm", "item", "role"])
            db = sqlite3.connect("data/economy.db"); c = db.cursor()
            
            c.execute("INSERT INTO server_shop_catalog (guild_id, name, price, rarity, emoji, weight, item_type, dm_message, use_message, role_name, is_default) VALUES (?,?,?,?,?,?,?,?,?,?,0)",
                      (interaction.guild_id, self.item_name.value, p, self.rarity, self.item_emoji.value, w, self.item_type, dm, use, role))
            db.commit(); db.close()
            await interaction.response.send_message(f"🎉 ✅ **{self.item_name.value}** was successfully added to the catalog!", ephemeral=True)
        except Exception as e: 
            await interaction.response.send_message(f"🛑 ❌ An error occurred: `{e}`", ephemeral=True)


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("data/economy.db")
        self.cursor = self.db.cursor()
        
        self.cursor.execute("CREATE TABLE IF NOT EXISTS bank (user_id INTEGER, guild_id INTEGER, coins INTEGER, last_daily TEXT, last_work INTEGER DEFAULT 0, PRIMARY KEY (user_id, guild_id))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS inventory (user_id INTEGER, guild_id INTEGER, item_name TEXT, amount INTEGER, PRIMARY KEY (user_id, guild_id, item_name))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS server_shop_catalog (item_id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, name TEXT, price INTEGER, rarity TEXT, emoji TEXT, weight INTEGER, item_type TEXT, dm_message TEXT, use_message TEXT, role_name TEXT, is_default INTEGER DEFAULT 0, UNIQUE(guild_id, name))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS eco_settings (guild_id INTEGER PRIMARY KEY, disable_defaults INTEGER DEFAULT 0)")
        
        self.cursor.execute("PRAGMA table_info(server_shop_catalog)")
        cols = [c[1] for c in self.cursor.fetchall()]
        if "is_default" not in cols:
            self.cursor.execute("ALTER TABLE server_shop_catalog ADD COLUMN is_default INTEGER DEFAULT 0")
            default_names = ["Water Bottle", "Coffee", "Burger", "Pizza", "Silver Coin", "Gold Ingot", "Diamond", "Premium VIP", "Billionaire", "Server Godfather", "The Chosen One", "Mystery Box"]
            for name in default_names:
                self.cursor.execute("UPDATE server_shop_catalog SET is_default = 1 WHERE name = ?", (name,))
        
        self.db.commit()

    def are_defaults_disabled(self, guild_id):
        self.cursor.execute("SELECT disable_defaults FROM eco_settings WHERE guild_id = ?", (guild_id,))
        res = self.cursor.fetchone()
        return res[0] if res else 0

    def get_user_data(self, u_id, g_id):
        self.cursor.execute("SELECT coins, last_daily, last_work FROM bank WHERE user_id = ? AND guild_id = ?", (u_id, g_id))
        res = self.cursor.fetchone()
        if not res:
            self.cursor.execute("INSERT INTO bank (user_id, guild_id, coins, last_daily, last_work) VALUES (?, ?, 0, '', 0)", (u_id, g_id))
            self.db.commit(); return (0, "", 0)
        return res

    def ensure_defaults(self, guild_id):
        self.cursor.execute("SELECT COUNT(*) FROM server_shop_catalog WHERE guild_id = ? AND is_default = 1", (guild_id,))
        if self.cursor.fetchone()[0] == 0:
            defaults = [
                (guild_id, "Water Bottle", 50, "Common", "💧", 80, "item", None, "{user} drinks a {item}. Refreshing! 🌊", None, 1),
                (guild_id, "Coffee", 100, "Common", "☕", 70, "item", None, "{user} drinks a {item}. Pure energy! ⚡", None, 1),
                (guild_id, "Burger", 200, "Common", "🍔", 60, "item", None, "{user} eats a juicy {item}! 😋", None, 1),
                (guild_id, "Pizza", 350, "Uncommon", "🍕", 50, "item", None, "{user} devours a whole {item}! 🧀", None, 1),
                (guild_id, "Silver Coin", 1500, "Uncommon", "🥈", 30, "item", None, "{user} polishes their {item}. Shiny! ✨", None, 1),
                (guild_id, "Gold Ingot", 15000, "Rare", "🧱", 15, "item", None, "{user} proudly shows off their {item}. 💰", None, 1),
                (guild_id, "Diamond", 75000, "Epic", "💎", 8, "item", None, "{user} sparkles with their {item}! 🌟", None, 1),
                (guild_id, "Premium VIP", 150000, "Rare", "⭐", 10, "role", None, None, "Premium", 1),
                (guild_id, "Billionaire", 1000000, "Epic", "💰", 5, "role", None, None, "Billionaire", 1),
                (guild_id, "Server Godfather", 5000000, "Legendary", "🥀", 2, "role", None, None, "Godfather", 1),
                (guild_id, "The Chosen One", 15000000, "Legendary", "🧬", 1, "role", None, None, "Chosen One", 1),
                (guild_id, "Mystery Box", 7500, "Uncommon", "🎁", 20, "dm", "You opened the box! 🗝️ Code: SECRET-99", None, None, 1)
            ]
            self.cursor.executemany("INSERT INTO server_shop_catalog (guild_id, name, price, rarity, emoji, weight, item_type, dm_message, use_message, role_name, is_default) VALUES (?,?,?,?,?,?,?,?,?,?,?)", defaults)
            self.db.commit()

    # --- ADMIN COMMANDS ---

    @app_commands.command(name="catalog", description="🛡️ Admin: View all registered items on this server.")
    @app_commands.describe(private="Should the list only be visible to you? (Recommended)")
    @app_commands.default_permissions(administrator=True)
    async def catalog(self, interaction: discord.Interaction, private: bool = True):
        self.ensure_defaults(interaction.guild_id)
        
        view = CatalogView(self, interaction.guild_id, interaction.guild.name, private)
        
        if not view.data and view.disabled_defaults:
            await interaction.response.send_message("🛑 📭 The catalog is empty because default items are disabled and no custom items exist.", view=view, ephemeral=private)
        else:
            await interaction.response.send_message(embed=view.create_embed(), view=view, ephemeral=private)

    @app_commands.command(name="additem", description="🛡️ Admin: Add a new item to the server catalog.")
    @app_commands.choices(rarity=[app_commands.Choice(name="Common ⚪", value="Common"), app_commands.Choice(name="Uncommon 🟢", value="Uncommon"), app_commands.Choice(name="Rare 🔵", value="Rare"), app_commands.Choice(name="Epic 🟣", value="Epic"), app_commands.Choice(name="Legendary 🟡", value="Legendary")],
                          item_type=[app_commands.Choice(name="Normal Item 📦", value="item"), app_commands.Choice(name="Discord Role 🎭", value="role"), app_commands.Choice(name="DM Message 📨", value="dm")])
    @app_commands.default_permissions(administrator=True)
    async def additem(self, interaction: discord.Interaction, rarity: app_commands.Choice[str], item_type: app_commands.Choice[str]):
        await interaction.response.send_modal(AddItemModal(rarity.value, item_type.value))

    @app_commands.command(name="removeitem", description="🛡️ Admin: Permanently delete an item from the catalog.")
    @app_commands.default_permissions(administrator=True)
    async def removeitem(self, interaction: discord.Interaction, item_name: str):
        self.cursor.execute("DELETE FROM server_shop_catalog WHERE guild_id = ? AND name COLLATE NOCASE = ?", (interaction.guild_id, item_name))
        if self.cursor.rowcount > 0:
            self.db.commit()
            await interaction.response.send_message(f"🗑️ ✅ **{item_name}** was successfully removed.", ephemeral=True)
        else:
            await interaction.response.send_message(f"🛑 ❌ **{item_name}** could not be found.", ephemeral=True)

    @app_commands.command(name="managecoins", description="🛡️ Admin: Manage user coins.")
    @app_commands.choices(action=[app_commands.Choice(name="Add ➕", value="add"), app_commands.Choice(name="Remove ➖", value="remove"), app_commands.Choice(name="Set 🎯", value="set")])
    @app_commands.default_permissions(administrator=True)
    async def managecoins(self, interaction: discord.Interaction, member: discord.Member, action: app_commands.Choice[str], amount: int):
        curr = self.get_user_data(member.id, interaction.guild_id)[0]
        new = curr + amount if action.value == "add" else max(0, curr - amount) if action.value == "remove" else amount
        self.cursor.execute("UPDATE bank SET coins = ? WHERE user_id = ? AND guild_id = ?", (new, member.id, interaction.guild_id))
        self.db.commit(); await interaction.response.send_message(f"🏦 ✅ {member.mention}'s new balance: **{new} 🪙**", ephemeral=True)

    @app_commands.command(name="admin_inventory", description="🛡️ Admin: View a user's inventory.")
    @app_commands.default_permissions(administrator=True)
    async def admin_inventory(self, interaction: discord.Interaction, member: discord.Member, private: bool = True):
        self.cursor.execute("SELECT item_name, amount FROM inventory WHERE user_id = ? AND guild_id = ?", (member.id, interaction.guild_id))
        res = self.fetchall()
        if not res: return await interaction.response.send_message(f"📭 🎒 {member.mention}'s inventory is empty.", ephemeral=private)
        
        embed = discord.Embed(title=f"🎒 Inventory of {member.name}", color=discord.Color.orange())
        for n, a in res:
            self.cursor.execute("SELECT emoji FROM server_shop_catalog WHERE name = ? AND guild_id = ?", (n, interaction.guild_id))
            e = self.cursor.fetchone()
            embed.add_field(name=f"{e[0] if e else '📦'} {n}", value=f"Amount: **x{a}**", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=private)

    @app_commands.command(name="admin_giveitem", description="🛡️ Admin: Give an item directly to a user's inventory.")
    @app_commands.default_permissions(administrator=True)
    async def admin_giveitem(self, interaction: discord.Interaction, member: discord.Member, item_name: str, amount: int = 1):
        self.cursor.execute("SELECT item_type, emoji, name, dm_message, role_name FROM server_shop_catalog WHERE name COLLATE NOCASE = ? AND guild_id = ?", (item_name, interaction.guild_id))
        res = self.cursor.fetchone()
        if not res: return await interaction.response.send_message("🛑 ❌ Item not found in the catalog.", ephemeral=True)
        
        if res[0] == "role":
            role = discord.utils.get(interaction.guild.roles, name=res[4] or res[2])
            if role: await member.add_roles(role)
            
        self.cursor.execute("INSERT INTO inventory (user_id, guild_id, item_name, amount) VALUES (?, ?, ?, ?) ON CONFLICT DO UPDATE SET amount = amount + ?", (member.id, interaction.guild_id, res[2], amount, amount))
        self.db.commit(); await interaction.response.send_message(f"🎁 ✅ You gave **{amount}x {res[1]} {res[2]}** to {member.mention}.", ephemeral=True)

    @app_commands.command(name="admin_removeinv", description="🛡️ Admin: Remove an item from a user's inventory.")
    @app_commands.default_permissions(administrator=True)
    async def admin_removeinv(self, interaction: discord.Interaction, member: discord.Member, item_name: str, amount: int = 1):
        self.cursor.execute("SELECT amount FROM inventory WHERE user_id = ? AND guild_id = ? AND item_name COLLATE NOCASE = ?", (member.id, interaction.guild_id, item_name))
        inv_res = self.cursor.fetchone()
        if not inv_res or inv_res[0] <= 0: return await interaction.response.send_message(f"🛑 ❌ {member.mention} does not own this item.", ephemeral=True)

        if inv_res[0] - amount > 0:
            self.cursor.execute("UPDATE inventory SET amount = amount - ? WHERE user_id = ? AND guild_id = ? AND item_name COLLATE NOCASE = ?", (amount, member.id, interaction.guild_id, item_name))
        else:
            self.cursor.execute("DELETE FROM inventory WHERE user_id = ? AND guild_id = ? AND item_name COLLATE NOCASE = ?", (member.id, interaction.guild_id, item_name))
            
        self.db.commit(); await interaction.response.send_message(f"🗑️ ✅ **{amount}x {item_name}** was removed from {member.mention}.", ephemeral=True)


    # --- USER COMMANDS ---

    @app_commands.command(name="top", description="🏆 View the server leaderboard.")
    @app_commands.choices(category=[
        app_commands.Choice(name="💰 Coins", value="coins"),
        app_commands.Choice(name="📈 Crypto Net Worth", value="crypto")
    ])
    async def top(self, interaction: discord.Interaction, category: app_commands.Choice[str]):
        if category.value == "coins":
            self.cursor.execute("SELECT user_id, coins FROM bank WHERE guild_id = ? ORDER BY coins DESC LIMIT 10", (interaction.guild_id,))
            top_users = self.cursor.fetchall()
            
            if not top_users:
                return await interaction.response.send_message("📭 🏆 The leaderboard is currently empty.", ephemeral=True)
                
            embed = discord.Embed(title=f"🏆 Top 10 Richest Users - Coins", color=discord.Color.gold())
            
            for idx, (u_id, coins) in enumerate(top_users, start=1):
                member = interaction.guild.get_member(u_id)
                name = member.display_name if member else f"Unknown User ({u_id})"
                medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"**{idx}.**"
                embed.add_field(name=f"{medal} {name}", value=f"**{coins} 🪙**", inline=False)
                
            await interaction.response.send_message(embed=embed)
            
        elif category.value == "crypto":
            self.cursor.execute("SELECT user_id, coin_name, amount FROM crypto_portfolio WHERE guild_id = ?", (interaction.guild_id,))
            portfolios = self.cursor.fetchall()
            
            if not portfolios:
                return await interaction.response.send_message("📭 📈 No one has invested in crypto yet on this server.", ephemeral=True)
                
            self.cursor.execute("SELECT name, price FROM crypto_market")
            market_prices = {name: price for name, price in self.cursor.fetchall()}
            
            user_totals = {}
            for u_id, coin_name, amount in portfolios:
                price = market_prices.get(coin_name, 0)
                val = amount * price
                user_totals[u_id] = user_totals.get(u_id, 0) + val
                
            sorted_users = sorted(user_totals.items(), key=lambda item: item[1], reverse=True)[:10]
            
            embed = discord.Embed(title=f"📈 Top 10 Crypto Investors", color=discord.Color.green())
            
            for idx, (u_id, total_val) in enumerate(sorted_users, start=1):
                member = interaction.guild.get_member(u_id)
                name = member.display_name if member else f"Unknown User ({u_id})"
                medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"**{idx}.**"
                embed.add_field(name=f"{medal} {name}", value=f"**{int(total_val)} 🪙** (Gross Value)", inline=False)
                
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shop", description="🛒 View today's shop rotation.")
    async def shop(self, interaction: discord.Interaction):
        self.ensure_defaults(interaction.guild_id)
        
        disabled = self.are_defaults_disabled(interaction.guild_id)
        if disabled:
            self.cursor.execute("SELECT name, price, rarity, emoji, weight FROM server_shop_catalog WHERE guild_id = ? AND is_default = 0", (interaction.guild_id,))
        else:
            self.cursor.execute("SELECT name, price, rarity, emoji, weight FROM server_shop_catalog WHERE guild_id = ?", (interaction.guild_id,))
        
        items = self.cursor.fetchall()
        total_items = len(items)
        
        if total_items == 0:
            return await interaction.response.send_message("📭 🛒 The shop is completely empty today!", ephemeral=True)
            
        # --- Fixed Dynamic Shop Size Logic ---
        if total_items <= 20:
            shop_size = 8
        elif total_items <= 40:
            shop_size = 14
        elif total_items <= 60:
            shop_size = 20
        else:
            shop_size = 25
            
        shop_size = min(shop_size, total_items)
        
        rnd = random.Random(f"{interaction.guild_id}{datetime.date.today().strftime('%Y%m%d')}")
        daily = []
        temp = list(items)
        
        for _ in range(shop_size):
            if not temp: break
            c = rnd.choices(temp, weights=[x[4] for x in temp], k=1)[0]
            daily.append(c)
            temp.remove(c)
            
        view = ShopView(daily)
        await interaction.response.send_message(embed=view.create_embed(), view=view)

    @app_commands.command(name="buy", description="🛍️ Buy an item from the shop.")
    async def buy(self, interaction: discord.Interaction, item_name: str):
        disabled = self.are_defaults_disabled(interaction.guild_id)
        if disabled:
            self.cursor.execute("SELECT price, name, item_type, role_name, dm_message, emoji FROM server_shop_catalog WHERE guild_id = ? AND name COLLATE NOCASE = ? AND is_default = 0", (interaction.guild_id, item_name))
        else:
            self.cursor.execute("SELECT price, name, item_type, role_name, dm_message, emoji FROM server_shop_catalog WHERE guild_id = ? AND name COLLATE NOCASE = ?", (interaction.guild_id, item_name))
            
        res = self.cursor.fetchone()
        if not res: return await interaction.response.send_message("🛑 ❌ Item not found in the active catalog.", ephemeral=True)
        
        p, rn, it, ron, dm, em = res
        c = self.get_user_data(interaction.user.id, interaction.guild_id)[0]
        if c < p: return await interaction.response.send_message(f"💸 ❌ Not enough coins! You are missing **{p - c} 🪙**.", ephemeral=True)
        
        if it == "role":
            role = discord.utils.get(interaction.guild.roles, name=ron or rn)
            if not role: role = await interaction.guild.create_role(name=ron or rn)
            if role in interaction.user.roles: return await interaction.response.send_message("🛑 ❌ You already own this rank!", ephemeral=True)
            await interaction.user.add_roles(role)
        elif it == "dm":
            try: await interaction.user.send(f"📦 🎁 Your purchased item **{rn}**: {dm}")
            except: return await interaction.response.send_message("🛑 ❌ Your server DMs are blocked!", ephemeral=True)

        self.cursor.execute("UPDATE bank SET coins = coins - ? WHERE user_id = ? AND guild_id = ?", (p, interaction.user.id, interaction.guild_id))
        self.cursor.execute("INSERT INTO inventory (user_id, guild_id, item_name, amount) VALUES (?, ?, ?, 1) ON CONFLICT DO UPDATE SET amount = amount + 1", (interaction.user.id, interaction.guild_id, rn))
        self.db.commit(); await interaction.response.send_message(f"🎉 🛍️ You successfully bought **{em} {rn}** for **{p} 🪙**!")

    @app_commands.command(name="balance", description="💰 Check your current balance.")
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None):
        m = member or interaction.user
        c = self.get_user_data(m.id, interaction.guild_id)[0]
        await interaction.response.send_message(f"🏦 💰 {m.display_name} currently has **{c} 🪙**.")

    @app_commands.command(name="daily", description="🎁 Claim your daily coin bonus!")
    async def daily(self, interaction: discord.Interaction):
        c, last, _ = self.get_user_data(interaction.user.id, interaction.guild_id)
        today = datetime.date.today().strftime("%Y-%m-%d")
        if last == today: return await interaction.response.send_message("🛑 ⏳ You have already claimed your daily bonus today!", ephemeral=True)
        
        self.cursor.execute("UPDATE bank SET coins = coins + 250, last_daily = ? WHERE user_id = ? AND guild_id = ?", (today, interaction.user.id, interaction.guild_id))
        self.db.commit(); await interaction.response.send_message("✨ 🎁 Yay! You received your daily **250 🪙**!")

    @app_commands.command(name="work", description="👷 Work to earn some quick coins.")
    async def work(self, interaction: discord.Interaction):
        u, g = interaction.user.id, interaction.guild_id
        _, _, lw = self.get_user_data(u, g)
        now = int(time.time())
        if now - lw < 3600: 
            mins, secs = divmod(3600 - (now - lw), 60)
            return await interaction.response.send_message(f"💦 ⏳ You are exhausted! Wait another **{mins}m {secs}s**.", ephemeral=True)
            
        e = random.randint(50, 150)
        self.cursor.execute("UPDATE bank SET coins = coins + ?, last_work = ? WHERE user_id = ? AND guild_id = ?", (e, now, u, g))
        self.db.commit(); await interaction.response.send_message(f"💼 💵 You worked hard and earned **{e} 🪙**!")

    @app_commands.command(name="inventory", description="🎒 Show your packed inventory.")
    async def inventory(self, interaction: discord.Interaction):
        self.cursor.execute("SELECT item_name, amount FROM inventory WHERE user_id = ? AND guild_id = ?", (interaction.user.id, interaction.guild_id))
        res = self.cursor.fetchall()
        if not res: return await interaction.response.send_message("📭 🎒 Your inventory is completely empty.")
        
        embed = discord.Embed(title="🎒 Your Inventory", color=discord.Color.blue())
        for n, a in res:
            self.cursor.execute("SELECT emoji FROM server_shop_catalog WHERE name = ? AND guild_id = ?", (n, interaction.guild_id))
            e = self.cursor.fetchone()
            embed.add_field(name=f"{e[0] if e else '📦'} {n}", value=f"Amount: **x{a}**", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="use", description="⚡ Use an item from your inventory.")
    async def use_item(self, interaction: discord.Interaction, item_name: str):
        self.cursor.execute("SELECT amount FROM inventory WHERE user_id = ? AND guild_id = ? AND item_name COLLATE NOCASE = ?", (interaction.user.id, interaction.guild_id, item_name))
        res = self.cursor.fetchone()
        if not res or res[0] <= 0: return await interaction.response.send_message("🛑 ❌ You do not own this item.", ephemeral=True)
        
        self.cursor.execute("SELECT item_type, emoji, name, use_message FROM server_shop_catalog WHERE name COLLATE NOCASE = ? AND guild_id = ?", (item_name, interaction.guild_id))
        cat = self.cursor.fetchone()
        if not cat or cat[0] in ["role", "dm"]: return await interaction.response.send_message("🛑 ❌ This item cannot be 'used' directly.", ephemeral=True)
        
        if res[0] == 1: 
            self.cursor.execute("DELETE FROM inventory WHERE user_id = ? AND guild_id = ? AND item_name COLLATE NOCASE = ?", (interaction.user.id, interaction.guild_id, item_name))
        else: 
            self.cursor.execute("UPDATE inventory SET amount = amount - 1 WHERE user_id = ? AND guild_id = ? AND item_name COLLATE NOCASE = ?", (interaction.user.id, interaction.guild_id, item_name))
        
        self.db.commit()
        msg = cat[3].replace("{user}", interaction.user.mention).replace("{item}", f"**{cat[1]} {cat[2]}**") if cat[3] else f"✨ ✅ You used {cat[1]} {cat[2]}."
        await interaction.response.send_message(msg)

    @app_commands.command(name="sell", description="♻️ Sell an item back for 50% of its original price.")
    async def sell_item(self, interaction: discord.Interaction, item_name: str, amount: int = 1):
        if amount <= 0: return await interaction.response.send_message("🛑 ❌ Invalid amount.", ephemeral=True)
        
        self.cursor.execute("SELECT amount FROM inventory WHERE user_id = ? AND guild_id = ? AND item_name COLLATE NOCASE = ?", (interaction.user.id, interaction.guild_id, item_name))
        res = self.cursor.fetchone()
        if not res or res[0] < amount: return await interaction.response.send_message("🛑 ❌ You don't have that many items.", ephemeral=True)
        
        self.cursor.execute("SELECT price, name, item_type FROM server_shop_catalog WHERE name COLLATE NOCASE = ? AND guild_id = ?", (item_name, interaction.guild_id))
        cat = self.cursor.fetchone()
        if not cat or cat[2] == "role": return await interaction.response.send_message("🛑 ❌ Ranks/Roles cannot be sold.", ephemeral=True)
        
        sell_p = int(cat[0] * 0.5) * amount
        if res[0] == amount: 
            self.cursor.execute("DELETE FROM inventory WHERE user_id = ? AND guild_id = ? AND item_name = ?", (interaction.user.id, interaction.guild_id, cat[1]))
        else: 
            self.cursor.execute("UPDATE inventory SET amount = amount - ? WHERE user_id = ? AND guild_id = ? AND item_name = ?", (amount, interaction.user.id, interaction.guild_id, cat[1]))
        
        c = self.get_user_data(interaction.user.id, interaction.guild_id)[0]
        self.cursor.execute("UPDATE bank SET coins = ? WHERE user_id = ? AND guild_id = ?", (c + sell_p, interaction.user.id, interaction.guild_id))
        self.db.commit(); await interaction.response.send_message(f"🤝 💸 You sold **x{amount} {cat[1]}** to the shop for **{sell_p} 🪙**!")

async def setup(bot):
    await bot.add_cog(Economy(bot))
