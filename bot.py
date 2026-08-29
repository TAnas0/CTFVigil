import os
import re
from dotenv import load_dotenv
import discord
from discord.ext import commands

from ctfvigil.client import CTFTimeClient
from ctfvigil.utils import create_event_embed

load_dotenv()


class CLIFlags(commands.FlagConverter, prefix="--", delimiter=":", case_insensitive=True):
    """CLI-style flag parser for CTF feed commands."""

    limit: int = commands.flag(default=5, description="Number of events to display")
    online: bool = commands.flag(default=False, description="Filter for online-only events")

    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str) -> "CLIFlags":
        arg = argument.strip()
        if arg.isdigit():
            arg = f"--limit:{arg}"
        else:
            arg = re.sub(r"--([a-zA-Z0-9_-]+)=", r"--\1:", arg)
            arg = re.sub(r"--([a-zA-Z0-9_-]+)\s+([^\s-]+)", r"--\1:\2", arg)
            arg = re.sub(r"--online(?!\S)(?!\s*:)", "--online:true", arg, flags=re.IGNORECASE)
        return await super().convert(ctx, arg)


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
ctf_client = CTFTimeClient()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")


@bot.command()
async def hello(ctx: commands.Context):
    await ctx.send(f"Hello, {ctx.author.name}!")


async def send_ctf_feed(ctx: commands.Context, limit: int, online: bool):
    """Fetch and send CTF events as individual messages for reaction-based tracking."""
    if limit < 1:
        await ctx.send("Please specify a limit of at least 1.")
        return

    limit = min(limit, 20)
    fetch_limit = limit * 2 if online else limit

    try:
        events = await ctf_client.fetch_upcoming_events(limit=fetch_limit)
    except Exception as exc:
        await ctx.send(f"❌ Error fetching CTF events: `{exc}`")
        return

    if online:
        events = [e for e in events if not e.get("onsite", False)]

    events = events[:limit]

    if not events:
        await ctx.send("No upcoming CTFs found matching your criteria.")
        return

    for event in events:
        await ctx.send(embed=create_event_embed(event))


@bot.command(name="ctfs", aliases=["upcomingctfs", "ctf"])
async def ctfs_cmd(ctx: commands.Context, *, flags: CLIFlags = CLIFlags()):
    """CLI-like CTF feed. Supports: !ctfs --limit 5 --online"""
    await send_ctf_feed(ctx, limit=flags.limit, online=flags.online)


@bot.command(name="upcoming")
async def upcoming_cmd(ctx: commands.Context, limit: int = 5):
    """Unfiltered upcoming CTF feed."""
    await send_ctf_feed(ctx, limit=limit, online=False)


@bot.command(name="onlinectfs", aliases=["upcoming_online"])
async def onlinectfs_cmd(ctx: commands.Context, limit: int = 5):
    """Online-only CTF feed."""
    await send_ctf_feed(ctx, limit=limit, online=True)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("DISCORD_TOKEN is not set in environment or .env file.")
