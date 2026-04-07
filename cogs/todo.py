import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class TodoList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("data/todo.db")
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task TEXT
            )
        """)
        self.db.commit()

    todo_group = app_commands.Group(name="todo", description="Manage your personal to-do list.")

    @todo_group.command(name="add", description="Add a new task to your to-do list.")
    async def todo_add(self, interaction: discord.Interaction, task: str):
        self.cursor.execute("INSERT INTO tasks (user_id, task) VALUES (?, ?)", (interaction.user.id, task))
        self.db.commit()
        await interaction.response.send_message(f"✅ Added to your list: `{task}`", ephemeral=True)

    @todo_group.command(name="list", description="Show your current to-do list.")
    async def todo_list(self, interaction: discord.Interaction):
        self.cursor.execute("SELECT task_id, task FROM tasks WHERE user_id = ?", (interaction.user.id,))
        tasks = self.cursor.fetchall()
        
        if not tasks:
            await interaction.response.send_message("✅ Your to-do list is empty. Good job!", ephemeral=True)
            return

        embed = discord.Embed(title=f"📝 {interaction.user.name}'s To-Do List", color=discord.Color.teal())
        
        description = ""
        for index, (task_id, task_text) in enumerate(tasks, start=1):
            description += f"**{index}.** {task_text} *(ID: {task_id})*\n"
            
        embed.description = description
        embed.set_footer(text="Use /todo remove [ID] to complete a task.")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @todo_group.command(name="remove", description="Remove a completed task from your list.")
    @app_commands.describe(task_id="The ID of the task you want to remove (check /todo list).")
    async def todo_remove(self, interaction: discord.Interaction, task_id: int):
        # Erst überprüfen, ob die Aufgabe dem User gehört
        self.cursor.execute("SELECT task FROM tasks WHERE task_id = ? AND user_id = ?", (task_id, interaction.user.id))
        result = self.cursor.fetchone()
        
        if not result:
            await interaction.response.send_message("❌ No task found with this ID on your list.", ephemeral=True)
            return
            
        self.cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        self.db.commit()
        
        await interaction.response.send_message(f"🗑️ Removed task: `{result[0]}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TodoList(bot))
