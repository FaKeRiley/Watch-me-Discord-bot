import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
from datetime import datetime

class AdminInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Stelle sicher, dass der data-Ordner existiert
        os.makedirs("data", exist_ok=True)
        
        # Erstelle/Verbinde mit der neuen Datenbank speziell für User-Logs
        self.db = sqlite3.connect("data/user_logs.db")
        self.cursor = self.db.cursor()
        
        # Erstelle die Tabelle, falls sie noch nicht existiert
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                action TEXT,
                reason TEXT,
                timestamp TEXT
            )
        ''')
        self.db.commit()

    def cog_unload(self):
        # Schließe die Datenbankverbindung sicher, wenn das Modul entladen wird
        self.db.close()

    # --- 1. Befehl: Einen Log-Eintrag hinzufügen ---
    @app_commands.command(name="addlog", description="Fügt einen Log-Eintrag (z.B. Warnung, Notiz) für einen User hinzu.")
    @app_commands.describe(
        user="Der User, der den Eintrag bekommt", 
        action="Art des Eintrags (z.B. Warn, Note, Kick, Ban)", 
        reason="Der Grund für diesen Eintrag"
    )
    @app_commands.default_permissions(administrator=True)
    async def addlog(self, interaction: discord.Interaction, user: discord.User, action: str, reason: str):
        # Aktuelles Datum und Uhrzeit
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # In die Datenbank schreiben
        self.cursor.execute('''
            INSERT INTO logs (guild_id, user_id, moderator_id, action, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (interaction.guild.id, user.id, interaction.user.id, action, reason, now))
        self.db.commit()
        
        # Ephemeral=True stellt sicher, dass nur Admins die Bestätigung sehen
        await interaction.response.send_message(f"✅ Eintrag für {user.mention} gespeichert:\n**Aktion:** {action}\n**Grund:** {reason}", ephemeral=True)


    # --- 2. Befehl: Die Akte eines Users einsehen ---
    @app_commands.command(name="admininfo", description="Zeigt die Moderations-Akte und Logs eines Users an.")
    @app_commands.describe(user="Der User, dessen Akte du sehen möchtest")
    @app_commands.default_permissions(administrator=True)
    async def admininfo(self, interaction: discord.Interaction, user: discord.User):
        # Lade alle Einträge für diesen User auf diesem Server, neuste zuerst
        self.cursor.execute('''
            SELECT moderator_id, action, reason, timestamp FROM logs
            WHERE guild_id = ? AND user_id = ?
            ORDER BY log_id DESC
        ''', (interaction.guild.id, user.id))
        
        logs = self.cursor.fetchall()

        # Das Embed für die Übersicht aufbauen
        embed = discord.Embed(title=f"📋 Admin Info & Akte: {user.display_name}", color=discord.Color.red())
        embed.set_thumbnail(url=user.display_avatar.url)

        if not logs:
            embed.description = "✅ Dieser User hat eine weiße Weste! Es wurden keine Einträge gefunden."
            embed.color = discord.Color.green()
        else:
            embed.description = f"Es wurden **{len(logs)}** Einträge für diesen User gefunden.\n"
            
            # Wir zeigen maximal die letzten 10 Einträge an, damit das Embed nicht das Limit sprengt
            for idx, log in enumerate(logs[:10]):
                mod_id, action, reason, timestamp = log
                
                embed.add_field(
                    name=f"{idx+1}. {action} ({timestamp})",
                    value=f"**Grund:** {reason}\n**Moderator:** <@{mod_id}>",
                    inline=False
                )
                
            if len(logs) > 10:
                embed.set_footer(text=f"Zeige 10 von {len(logs)} Einträgen an.")
            else:
                embed.set_footer(text="Ende der Akte.")

        # Antwort nur für den ausführenden Admin sichtbar machen
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminInfo(bot))
