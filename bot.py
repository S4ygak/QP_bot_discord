import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- КЛАСС КНОПКИ ---
class RoleButton(discord.ui.Button):
    def __init__(self, role_id: int, label: str, emoji: str):
        super().__init__(style=discord.ButtonStyle.primary, label=label, emoji=emoji, custom_id=f"role:{role_id}")
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        role = interaction.guild.get_role(self.role_id)
        if not role:
            await interaction.followup.send("⚠️ Роль не найдена на сервере.", ephemeral=True)
            return

        member = interaction.user
        if role in member.roles:
            await member.remove_roles(role)
            await interaction.followup.send(f"➖ Роль **{role.name}** снята.", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.followup.send(f"✅ Роль **{role.name}** выдана.", ephemeral=True)

# --- КЛАСС ПАНЕЛИ (VIEW) ---
class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 
        
        # ЗДЕСЬ МЫ ДОБАВЛЯЕМ РОЛИ В ПАНЕЛЬ (ID, Название, Эмодзи)
        roles_config = [
            (1566862684861767801, "Ого!", "🧪"),
            (1566862708391813190, "Че!", "🎮"),
            (1566862712254898337, "Ладно!", "🎨"),
            (1566862714746314993, "Текст!", "🔔"),
        ]
        
        for r_id, r_label, r_emoji in roles_config:
            self.add_item(RoleButton(role_id=r_id, label=r_label, emoji=r_emoji))

# --- СОБЫТИЯ ---
@bot.event
async def on_ready():
    # Регистрируем панель
    bot.add_view(RoleView())
    
    # Синхронизируем слэш-команды с Discord (чтобы они появились в меню)
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано {len(synced)} слэш-команд.")
    except Exception as e:
        print(f"Ошибка синхронизации команд: {e}")
        
    print(f'Бот {bot.user} готов к работе!')

# --- СЛЭШ-КОМАНДА ---
# default_permissions(manage_roles=True) значит, что команду увидят только те, 
# у кого есть право "Управлять ролями" (Админы)
@bot.tree.command(name="panel", description="Отправить панель с ролями в этот канал")
@app_commands.default_permissions(manage_roles=True)
async def panel(interaction: discord.Interaction):
    await interaction.response.send_message("Выберите роли, нажав на кнопки ниже:", view=RoleView())

if __name__ == '__main__':
    bot.run(TOKEN)