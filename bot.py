import discord
from discord.ext import commands
from discord import app_commands
import os
import aiosqlite
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
DB_NAME = "roles.db"

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
async def init_db():
    """Создает таблицу, если ее нет"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                guild_id INTEGER,
                role_id INTEGER,
                label TEXT,
                emoji TEXT,
                PRIMARY KEY (guild_id, role_id)
            )
        ''')
        await db.commit()

async def get_guild_roles(guild_id: int):
    """Получает список ролей для конкретного сервера"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT role_id, label, emoji FROM roles WHERE guild_id = ?", (guild_id,)) as cursor:
            return await cursor.fetchall()

# --- КЛАСС КНОПКИ ---
class RoleButton(discord.ui.Button):
    def __init__(self, role_id: int, label: str, emoji: str):
        super().__init__(style=discord.ButtonStyle.primary, label=label, emoji=emoji, custom_id=f"role:{role_id}")
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        role = interaction.guild.get_role(self.role_id)
        if not role:
            await interaction.followup.send("⚠️ Роль была удалена с сервера ><", ephemeral=True)
            return

        member = interaction.user
        if role in member.roles:
            await member.remove_roles(role)
            await interaction.followup.send(f"➖ Роль **{role.name}** снята!", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.followup.send(f"✅ Роль **{role.name}** выдана!", ephemeral=True)

# --- КЛАСС ПАНЕЛИ (VIEW) ---
# Теперь View создается динамически на основе того, что лежит в базе
class RoleView(discord.ui.View):
    def __init__(self, roles_data: list):
        super().__init__(timeout=None) 
        for r_id, r_label, r_emoji in roles_data:
            self.add_item(RoleButton(role_id=r_id, label=r_label, emoji=r_emoji))

# --- СОБЫТИЯ ---
@bot.event
async def on_ready():
    await init_db() # Инициализируем базу при старте
    
    # Регистрируем панели, чтобы кнопки работали после перезапуска
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT DISTINCT guild_id FROM roles") as cursor:
            guilds = await cursor.fetchall()
            for (guild_id,) in guilds:
                roles_data = await get_guild_roles(guild_id)
                if roles_data:
                    bot.add_view(RoleView(roles_data)) # "Вспоминаем" кнопки для каждого сервера

    # ГЛОБАЛЬНАЯ синхронизация (для всех серверов сразу)
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано {len(synced)} глобальных слэш-команд.")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")
        
    print(f'Бот {bot.user} готов к работе!')

# --- КОМАНДА: ДОБАВИТЬ РОЛЬ В ПАНЕЛЬ ---
@bot.tree.command(name="addrole", description="Добавить роль в панель выдачи")
@app_commands.default_permissions(manage_roles=True) # Только для админов
@app_commands.describe(
    role="Выберите роль, которую хотите выдавать!",
    label="Текст на кнопке (например: Игрок)!",
    emoji="Эмодзи для кнопки (необязательно)!"
)
async def addrole(interaction: discord.Interaction, role: discord.Role, label: str, emoji: str = None):
    # Проверка: бот не может выдать роль выше своей
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("❌ Бау вау :( Я не могу управлять этой ролью, так как она выше моей в списке ролей!", ephemeral=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        # Сохраняем в базу
        await db.execute(
            "INSERT OR REPLACE INTO roles (guild_id, role_id, label, emoji) VALUES (?, ?, ?, ?)",
            (interaction.guild_id, role.id, label, emoji)
        )
        await db.commit()
    
    await interaction.response.send_message(f"✅ Бваоваф! :) Роль **{role.name}** успешно добавлена в базу! Не забудьте отправить `/panel`!", ephemeral=True)

# --- КОМАНДА: ОТПРАВИТЬ ПАНЕЛЬ ---
@bot.tree.command(name="panel", description="Отправить панель с ролями в этот канал")
@app_commands.default_permissions(manage_roles=True)
async def panel(interaction: discord.Interaction):
    roles_data = await get_guild_roles(interaction.guild_id)
    
    if not roles_data:
        await interaction.response.send_message("❌ Не клюй меня, пожалуйста >< На этом сервере еще нет настроенных ролей! Используйте `/addrole`!", ephemeral=True)
        return

    await interaction.response.send_message("Выберите роли, нажав на кнопки ниже (!):", view=RoleView(roles_data))

if __name__ == '__main__':
    bot.run(TOKEN)