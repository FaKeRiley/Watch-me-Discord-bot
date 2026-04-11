import discord
from discord.ext import commands, tasks
import sqlite3
import os
import time

class DataCleanup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Stelle sicher, dass der data-Ordner existiert
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Eigene Datenbank zum Tracken der Server-Aktivität und geplanten Löschungen
        self.activity_db_path = os.path.join(self.data_dir, "activity.db")
        self.init_activity_db()
        
        # Starte den Loop, der einmal am Tag (24 Stunden) aufräumt
        self.cleanup_loop.start()

    def init_activity_db(self):
        """Erstellt die Tabellen für Aktivität und Schonfristen."""
        conn = sqlite3.connect(self.activity_db_path)
        cursor = conn.cursor()
        
        # Tabelle 1: Reguläre Inaktivität (60 Tage)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_activity (
                guild_id INTEGER PRIMARY KEY,
                last_active REAL
            )
        ''')
        
        # Tabelle 2: Geplante Löschungen nach Rauswurf (7 Tage Schonfrist)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_deletions (
                guild_id INTEGER PRIMARY KEY,
                leave_time REAL
            )
        ''')
        
        conn.commit()
        conn.close()

    def update_activity(self, guild_id: int):
        """Aktualisiert den Zeitstempel der letzten Aktivität für einen Server."""
        if guild_id is None:
            return
            
        current_time = time.time()
        try:
            conn = sqlite3.connect(self.activity_db_path, timeout=10.0)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO server_activity (guild_id, last_active)
                VALUES (?, ?)
            ''', (guild_id, current_time))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Fehler beim Speichern der Aktivität für Server {guild_id}: {e}")

    # --- 1. Aktivität tracken ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        self.update_activity(message.guild.id)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.guild:
            return
        self.update_activity(interaction.guild.id)

    # --- 2. Wenn der Bot von einem Server entfernt wird ---
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        current_time = time.time()
        try:
            conn = sqlite3.connect(self.activity_db_path, timeout=10.0)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO pending_deletions (guild_id, leave_time)
                VALUES (?, ?)
            ''', (guild.id, current_time))
            conn.commit()
            conn.close()
            print(f"[Cleanup] Bot wurde von Server {guild.name} ({guild.id}) entfernt. Datenlöschung in 7 Tagen markiert.")
        except Exception as e:
            print(f"Fehler beim Markieren der Löschung für Server {guild.id}: {e}")

    # --- 3. Wenn der Bot innerhalb der 7 Tage wieder eingeladen wird ---
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        try:
            conn = sqlite3.connect(self.activity_db_path, timeout=10.0)
            cursor = conn.cursor()
            # Falls er in der Liste stand, wird er jetzt gerettet
            cursor.execute('DELETE FROM pending_deletions WHERE guild_id = ?', (guild.id,))
            conn.commit()
            conn.close()
            
            # Aktivität sofort erneuern
            self.update_activity(guild.id)
            print(f"[Cleanup] Bot ist Server {guild.name} ({guild.id}) beigetreten. Evtl. geplante Löschung wurde storniert.")
        except Exception as e:
            pass

    # --- 4. Die eigentliche Bereinigung der Datenbanken ---
    def wipe_guild_data(self, guild_id: int):
        """Löscht alle Daten einer guild_id aus allen DBs außer den ignorierten."""
        ignored_dbs = ["birthdays.db", "pfp_and_banner.db", "activity.db"]
        deleted_records = 0
        
        for filename in os.listdir(self.data_dir):
            if not filename.endswith(".db") or filename in ignored_dbs:
                continue
                
            db_path = os.path.join(self.data_dir, filename)
            
            try:
                conn = sqlite3.connect(db_path, timeout=10.0)
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                for table_tuple in tables:
                    table_name = table_tuple[0]
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    if "guild_id" in columns:
                        cursor.execute(f"DELETE FROM {table_name} WHERE guild_id = ?", (guild_id,))
                        deleted_records += cursor.rowcount
                
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Fehler beim Bereinigen von {filename} für Server {guild_id}: {e}")
                
        return deleted_records

    # --- 5. Der Background-Task (läuft alle 24 Stunden) ---
    @tasks.loop(hours=24)
    async def cleanup_loop(self):
        await self.bot.wait_until_ready()
        
        sixty_days_sec = 60 * 24 * 60 * 60
        seven_days_sec = 7 * 24 * 60 * 60
        current_time = time.time()
        
        try:
            conn = sqlite3.connect(self.activity_db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # 1. Inaktive Server finden (60 Tage)
            cursor.execute('SELECT guild_id, last_active FROM server_activity')
            all_servers = cursor.fetchall()
            servers_to_delete_inactivity = [g_id for g_id, l_act in all_servers if (current_time - l_act) > sixty_days_sec]
            
            # 2. Verlassene Server finden (7 Tage Schonfrist abgelaufen)
            cursor.execute('SELECT guild_id, leave_time FROM pending_deletions')
            left_servers = cursor.fetchall()
            servers_to_delete_left = [g_id for g_id, l_time in left_servers if (current_time - l_time) > seven_days_sec]
            
            # Listen kombinieren (set verhindert doppelte Einträge)
            all_to_delete = set(servers_to_delete_inactivity + servers_to_delete_left)
            
            # Gefundene Server bereinigen
            for guild_id in all_to_delete:
                reason = "Inaktivität (60 Tage)" if guild_id in servers_to_delete_inactivity else "Verlassen (7 Tage abgelaufen)"
                print(f"[Cleanup] Server {guild_id} wird gelöscht. Grund: {reason}")
                
                self.wipe_guild_data(guild_id)
                
                # Nach dem Löschen aus unseren Kontroll-Tabellen entfernen
                cursor.execute('DELETE FROM server_activity WHERE guild_id = ?', (guild_id,))
                cursor.execute('DELETE FROM pending_deletions WHERE guild_id = ?', (guild_id,))
                
            conn.commit()
            conn.close()
            
            if all_to_delete:
                print(f"[Cleanup] Erfolgreich die Daten von {len(all_to_delete)} Servern gelöscht.")
                
        except Exception as e:
            print(f"Fehler im Cleanup-Loop: {e}")

    def cog_unload(self):
        self.cleanup_loop.cancel()

async def setup(bot):
    await bot.add_cog(DataCleanup(bot))
