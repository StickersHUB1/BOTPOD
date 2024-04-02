import discord
from discord.ext import commands
from datetime import datetime
import os
import sys
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Bot configuration
TOKEN = '${{ secrets.botpodtoken }}'

# Create an instance of Intents with message intent enabled
intents = discord.Intents.default()
intents.messages = True

# Create an instance of the bot with Intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Database of registered users and related prizes
registered_users = {}
related_prizes = {}

# WAX prizes
PRIZES_WAX = {
    50: 0.5,
    75: 1,
    100: 2
}

# Function to calculate user level
def calculate_level(registered_prizes):
    if registered_prizes >= 10:
        level = 1
        required_prizes = 10
        while registered_prizes >= required_prizes:
            level += 1
            required_prizes *= 2  # Duplica la cantidad de premios requeridos para el siguiente nivel
        return level - 1  # Resta 1 porque el bucle se detiene cuando los premios registrados superan los requeridos
    else:
        return 0

# Function to check if a user has won WAX prizes
def check_wax_winner(user_id, registered_prizes):
    wax_prize = 0
    for num_prizes, wax in PRIZES_WAX.items():
        if registered_prizes >= num_prizes:
            wax_prize += wax
    return wax_prize

# Command to register the user's WAX wallet
@bot.command()
async def register(ctx, wax_wallet=None):
    if wax_wallet is None:
        await ctx.send(':warning: You must include your WAX wallet. Example: `!register <waxwallet>`')
        return
    
    user_id = ctx.author.id
    if user_id in registered_users:
        await ctx.send(':x: You already have a registered wallet.')
        return
    registered_users[user_id] = wax_wallet
    await ctx.send(f':white_check_mark: Wallet registered: {wax_wallet}')
    await ctx.send(':tada: Well done! You have registered your WAX wallet successfully.')

# Command to register a prize
@bot.command()
async def regprize(ctx, *, prize=None):
    user_id = ctx.author.id
    
    if prize is None:
        await ctx.send(':warning: You must include the prize. Example: `!regprize <prizename>`')
        return
    
    # Check if the user has registered a WAX wallet
    if user_id not in registered_users:
        await ctx.send(':sob: To register a prize you need to register your wax wallet first.')
        return

    # Get the current date in YYYY-MM-DD format
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Check if the user already has registered prizes
    if user_id in related_prizes:
        # Check if there are registered prizes for the current date
        if current_date in related_prizes[user_id]:
            # Extend the existing list of prizes
            related_prizes[user_id][current_date].append(prize)
        else:
            # Create a new entry for the current date
            related_prizes[user_id][current_date] = [prize]
    else:
        # Create a new entry for the user and the current date
        related_prizes[user_id] = {current_date: [prize]}
    
    # Count the total number of prizes registered by the user
    total_prizes = sum(len(prizes) for prizes in related_prizes.get(user_id, {}).values())
    
    # Check if the user has reached a new level
    current_level = calculate_level(total_prizes)
    previous_level = calculate_level(total_prizes - 1)  # Subtract 1 to consider the current prize
    
    # Prepare the message
    message = f':white_check_mark: Prize registered: {prize} - {current_date}\n'
    if current_level > previous_level:
        message += f':trophy: Congratulations! You have registered your {total_prizes}th prize and leveled up to level {current_level}!\n'
    if total_prizes in PRIZES_WAX:
        wax_prize = PRIZES_WAX[total_prizes]
        message += f':tada: Congratulations! You have won {wax_prize} WAX.\n'
    message += '-\n:warning: Warning! Registering unclaimed prizes will not be counted.'
    
    await ctx.send(message)


@bot.command()
async def profile(ctx):
    user_id = ctx.author.id
    
    if user_id not in registered_users:
        await ctx.send(':sob: To see your profile you need to register your wax wallet first.')
        return
    
    registered_prizes = sum(len(prizes) for prizes in related_prizes.get(user_id, {}).values())
    level = calculate_level(registered_prizes)
    wax_earned = check_wax_winner(user_id, registered_prizes)
    
    # Create embed
    embed = discord.Embed(title="User Profile", description="Here's your profile information:", color=discord.Color.gold())
    embed.add_field(name="Level", value=level, inline=False)
    embed.add_field(name="Registered Prizes", value=registered_prizes, inline=False)
    embed.add_field(name="Total Wax Earned", value=f"{wax_earned} WAX", inline=False)
    
    await ctx.send(embed=embed)


@bot.command()
async def waxprizes(ctx):
    # Create embed
    embed = discord.Embed(title="Available Prizes", description="Here's the list of available prizes:", color=discord.Color.green())
    
    # Add each prize to the embed
    for prize_num, wax_prize in PRIZES_WAX.items():
        embed.add_field(name=f"{prize_num} Registered Prizes", value=f"{wax_prize} WAX", inline=False)
    
    await ctx.send(embed=embed)


# Command to search for prizes related to the user's wallet
@bot.command()
async def research(ctx):
    user_id = ctx.author.id
    
    if user_id not in registered_users:
        await ctx.send(':sob: To search your prizes history you must register your wax wallet first.')
        return
    
    if user_id not in related_prizes:
        await ctx.send('No prizes found related to your wallet')
        await ctx.send('You need to register some prize first.')
        await ctx.send('Note: Only the latest 20 prizes will be displayed.')
        return
    
    prizes_by_date = related_prizes[user_id]
    if not prizes_by_date:
        await ctx.send('No prizes found related to your wallet')
        await ctx.send('You need to register some prize first.')
        await ctx.send('Note: Only the latest 20 prizes will be displayed.')
        return
    
    message = ':trophy:Related prizes (showing the latest 20):\n'
    count = 0
    # Obtener las fechas ordenadas en orden cronológico descendente
    dates_sorted = sorted(prizes_by_date.keys(), reverse=True)
    for date in dates_sorted:
        prizes = prizes_by_date[date]
        for prize in reversed(prizes):  # Revertir la lista de premios para mostrar el más reciente primero
            if count >= 20:
                break
            message += f'{prize} - {date}\n'  # Mostrar cada premio y su fecha
            count += 1
    await ctx.send(message)

# Command to show the list of available commands
@bot.command()
async def info(ctx):
    embed = discord.Embed(title=":scroll: List of Commands", description="Here's the list of available commands:", color=discord.Color.blue())
    embed.add_field(name="!hi", value="Meet BotPod!.", inline=False)
    embed.add_field(name="!register <waxwallet>", value="Register your waxwallet wallet.", inline=False)
    embed.add_field(name="!play", value="Get the link to play the game.", inline=False)
    embed.add_field(name="!regprize <prizename>", value="Register a prize.", inline=False)
    embed.add_field(name="!profile", value="Show your user profile.", inline=False)
    embed.add_field(name="!research", value="Search for prizes related to your wallet.", inline=False)
    embed.add_field(name="!withdraw", value="Submit a request to withdraw your WAX.", inline=False)
    embed.add_field(name="!waxprizes", value="Show WAX prizes list.", inline=False)
    
    
    await ctx.send(embed=embed)

# Command to send the play link
@bot.command()
async def play(ctx):
    await ctx.send(":video_game: Here's the link to play! \nhttps://stickershub1.github.io/Profit-Tracker-System/")

@bot.command()
async def restart(ctx):
    await ctx.send("Restarting bot...")
    python = sys.executable
    try:
        os.execl(python, python, *sys.argv)
    except Exception as e:
        await ctx.send(f"An error occurred while restarting the bot: {e}")

@bot.command()
async def hi(ctx):
    # Parte 1
    explanation_part1 = """
    👋 Greetings, traveler, and welcome to the realm of BotPods within the expansive universe of StickersHUB1. 🌌
   I am BotPod, your faithful companion here on Discord, dedicated to assisting you on your journey through this cosmic domain. 🤖✨
    """
    await ctx.send(explanation_part1)

    # Parte 2
    explanation_part2 = """
    As guardians of this celestial realm, BotPods serve a crucial role in preserving its integrity and purity. Created by an enigmatic scientist, we stand as sentinels against the encroaching darkness. ⚔️🛡️
    """
    await ctx.send(explanation_part2)

    # Parte 3
    explanation_part3 = """
    The universe has been invaded by creatures from the underworld, leaving behind only pollution, ruins, and scarce signs of life... ☠️🌍
    """
    await ctx.send(explanation_part3)

    # Parte 4
    explanation_part4 = """
    On our planet, a mysterious scientist created the BotPods to shield us from the universe's contamination. They became the guardians, protecting and purifying the universe. 🌱🔬
    """
    await ctx.send(explanation_part4)

    # Parte 5
    explanation_part5 = """
    Over time, divine creatures appeared, choosing to accompany the BotPods on their mission. These divine beings possess unimaginable power, capable of granting wishes. However, they had lost hope that anyone with kindness would come to aid the universe, so they identify with the BotPods and join them on their adventures. ✨👼
    """
    await ctx.send(explanation_part5)

    # Parte 6
    explanation_part6 = """
    Earth became one of the cleanest or least polluted places in the universe or the Milky Way, attracting new species from other planets seeking refuge, peace, and tranquility. 🌎🌟
    """
    await ctx.send(explanation_part6)

    # Parte 7
    explanation_part7 = """
    Among these new species were tiny yet powerful beings called Quokkamara, as adorable as Quokkas and as large as Marmots. Despite their sweet and friendly appearance, they were demon hunters, known as the Profit Tracker Critters. They eliminated creatures that disturbed the peace and integrity of the earth. Some people supported them by donating money to improve their equipment, and in return, they shared the benefits they obtained from their adventures. 🐾🎖️
    """
    await ctx.send(explanation_part7)

    # Parte 8
    explanation_part8 = """
    Be part of the adventure and join the profit tracker critters!
    Not only that, if you're worthy of having a divine companion, ask for 1 daily wish! 🌟🌈
    """
    await ctx.send(explanation_part8)

    # Parte 9
    explanation_part9 = """
    All this and much more await you here! [Visit our website](https://stickershub1.github.io/Profit-Tracker-System/) 🖥️🔗
    """
    await ctx.send(explanation_part9)

from discord.ext.commands import Context

# Definir función de verificación personalizada para verificar si el mensaje es del mismo autor y canal
def is_same_author_and_channel(ctx: Context):
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel
    return check

@bot.command()
async def withdraw(ctx, wax_amount: float = None):
    # Obtener la información del usuario que solicitó el retiro
    user = ctx.author
    
    # Verificar si el usuario ha registrado una billetera WAX
    if user.id not in registered_users:
        await ctx.send(':sob: To Withdraw your WAX you must register your wax wallet first.')
        return
    
    # Verificar si el usuario tiene WAX en su perfil
    if user.id not in related_prizes or sum(len(prizes) for prizes in related_prizes[user.id].values()) == 0:
        await ctx.send(':sob: To Withdraw your WAX you must Earn some WAX first.')
        return
    
    # Calcular la cantidad de WAX disponible para retirar
    total_wax_earned = check_wax_winner(user.id, sum(len(prizes) for prizes in related_prizes.get(user.id, {}).values()))
    
    # Si no se especifica la cantidad de WAX a retirar, mostrar la cantidad disponible
    if wax_amount is None:
        await ctx.send(f"How much WAX do you want to withdraw? You have {total_wax_earned} WAX available.")

        # Esperar la respuesta del usuario
        try:
            response = await bot.wait_for('message', check=is_same_author_and_channel(ctx), timeout=60)
            wax_amount = float(response.content)
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond.")
            return
        except ValueError:
            await ctx.send("Invalid input. Please enter a valid number.")
            return
    
    # Verificar si el usuario tiene suficiente WAX para retirar
    if total_wax_earned < wax_amount:
        await ctx.send(":warning: You don't have enough WAX to withdraw.")
        return
    
    # Enviar una notificación al administrador con los detalles del retiro solicitado
    admin_notification = f"Solicitud de retiro de {wax_amount} WAX de {user.name} ({user.id})."
    await ctx.send(":mailbox_with_mail: Your withdrawal request has been sent to the administrator.")
    
    # Cambiar "tu_id" por tu ID de Discord para recibir la notificación
    admin_id = "331905464755421184"  # Reemplaza esto con tu ID de Discord
    admin_user = bot.get_user(admin_id)
    if admin_user:
        await admin_user.send(admin_notification)
    else:
        await ctx.send(":warning: Unable to send notification to the administrator.")

    # Responder al usuario con un mensaje de confirmación
    await ctx.send(f":white_check_mark: Your withdrawal request of {wax_amount} WAX has been received. "
                   "It will be processed within 12 to 24 hours.")




def start_bot():
    # Start the bot
    bot.run(TOKEN)

def restart_bot():
    python = sys.executable
    try:
        os.execl(python, python, *sys.argv)
    except Exception as e:
        print(f"An error occurred while restarting the bot: {e}")

class MyFileSystemEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            print("Detected change in Python files. Restarting bot...")
            restart_bot()

if __name__ == "__main__":
    observer = Observer()
    observer.schedule(MyFileSystemEventHandler(), path='.', recursive=True)
    observer.start()

    try:
        start_bot()
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
