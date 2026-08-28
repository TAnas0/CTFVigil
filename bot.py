import os
from dotenv import load_dotenv
import discord
from discord.ext import commands

# Define required permissions (intents)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello, {ctx.author.name}!")


load_dotenv()
bot.run(os.getenv("DISCORD_TOKEN"))
