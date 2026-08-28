import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
import aiohttp
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

def format_time_remaining(start_iso):
    # Parse the ISO start string into a timezone-aware datetime object
    start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    now_dt = datetime.now(timezone.utc)
    
    diff = start_dt - now_dt
    total_seconds = int(diff.total_seconds())
    
    if total_seconds <= 0:
        return "Started or in progress!"
        
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    
    return f"in {' '.join(parts)}"

@bot.command()
async def upcomingctfs(ctx):
    now = int(time.time())
    url = f"https://ctftime.org/api/v1/events/?limit=3&start={now}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                await ctx.send("Failed to reach the CTFtime API.")
                return
            
            events = await response.json()
            if not events:
                await ctx.send("No upcoming CTFs found.")
                return
            
            for event in events[:3]:
                name = event.get("title")
                ctftime_link = event.get("ctftime_url")
                event_url = event.get("url") or ctftime_link
                format_type = event.get("format", "Unknown")
                
                start_iso = event.get("start")
                friendly_countdown = format_time_remaining(start_iso)
                
                orgs = event.get("organizers", [])
                org_name = orgs[0].get("name") if orgs else "Unknown"
                
                desc = event.get("description", "No description provided.")
                if len(desc) > 250:
                    desc = desc[:247] + "..."
                    
                logo = event.get("logo")
                
                embed = discord.Embed(
                    title=name,
                    url=event_url,
                    description=desc,
                    color=discord.Color.dark_purple()
                )
                
                if logo:
                    embed.set_thumbnail(url=logo)
                    
                embed.add_field(name="⏰ Starts", value=friendly_countdown, inline=True)
                embed.add_field(name="🏛️ Organizer", value=org_name, inline=True)
                embed.add_field(name="🏆 Format", value=format_type, inline=True)
                embed.add_field(name="🔗 CTFtime", value=f"[Page]({ctftime_link})", inline=True)
                
                await ctx.send(embed=embed)

load_dotenv()
bot.run(os.getenv("DISCORD_TOKEN"))
