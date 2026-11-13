import os
import re
from dotenv import load_dotenv
import discord
from discord.ext import commands

from ctfvigil.client import CTFTimeClient
from ctfvigil.clients.ctfd import CTFdClient
from ctfvigil.utils import create_event_embed
from ctfvigil import __version__

from tasks.tasks import sync_ctftime_events_task, check_ctfd_ctf

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
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)
ctf_client = CTFTimeClient()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")


@bot.command()
async def hello(ctx: commands.Context):
    await ctx.send(f"Hello, {ctx.author.name}!")


@bot.command(name="vigil", aliases=["commands", "guide"])
async def vigil_help(ctx: commands.Context):
    """Display CTFVigil's full command reference."""
    embed = discord.Embed(
        title="🦉 CTFVigil Command Reference",
        description=(
            f"Vigilant CTF ops assistant • v{__version__}\nAll commands use the `!` prefix."
        ),
        color=discord.Color.dark_purple(),
    )

    # ── CTFtime Feed ──────────────────────────────────────────────
    embed.add_field(
        name="📡 CTF Feed",
        value=(
            "`!ctfs [--limit N] [--online]`\n"
            "Fetch upcoming CTFs from CTFtime with CLI-style flags.\n"
            "Aliases: `!upcomingctfs`, `!ctf`\n\n"
            "`!upcoming [N]`\n"
            "Unfiltered upcoming CTF feed (default: 5).\n\n"
            "`!onlinectfs [N]`\n"
            "Online-only CTF feed shortcut.\n"
            "Alias: `!upcoming_online`"
        ),
        inline=False,
    )

    # ── Flag examples ─────────────────────────────────────────────
    embed.add_field(
        name="🚩 Feed Flag Examples",
        value=(
            "`!ctfs --limit 10` — show 10 events\n"
            "`!ctfs --online` — online events only\n"
            "`!ctfs --limit 3 --online` — 3 online events\n"
            "`!ctfs 8` — shorthand for `--limit 8`"
        ),
        inline=False,
    )

    # ── CTFd Integration ──────────────────────────────────────────
    embed.add_field(
        name="🎯 CTFd Platform Ops",
        value=(
            "`!track <url>`\n"
            "Fingerprint a CTFd instance and probe its public API endpoints\n"
            "(`/users`, `/teams`, `/challenges`, `/scoreboard`).\n"
            "Aliases: `!inspect`, `!probe`\n\n"
            "`!scoreboard <url>`\n"
            "Fetch and display the live public leaderboard standings.\n"
            "Aliases: `!standings`, `!lb`, `!leaderboard`"
        ),
        inline=False,
    )

    # ── Reactions ─────────────────────────────────────────────────
    embed.add_field(
        name="⚡ Reaction Controls",
        value=(
            "React to any CTFVigil event embed with:\n"
            "🎯 — **Acquire target** — marks the CTF as a team objective\n"
            "*(More reaction actions coming in Phase 2)*"
        ),
        inline=False,
    )

    # ── Tips ──────────────────────────────────────────────────────
    embed.add_field(
        name="💡 Tips",
        value=(
            "• CTFtime feed caps at **20 events** max per command.\n"
            "• `!track` works anonymously — no credentials needed.\n"
            "• Protected endpoints (`401`/`403`) just mean auth is required.\n"
            "• Self-hosting? See the [GitHub repo](https://github.com/ctfvigil/CTFVigil)."
        ),
        inline=False,
    )

    embed.set_footer(text="CTFVigil • github.com/ctfvigil/CTFVigil • Apache 2.0")
    await ctx.send(embed=embed)


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
async def ctfs_cmd(ctx: commands.Context, *, flags: CLIFlags):
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


@bot.command(name="track", aliases=["inspect", "probe"])
async def track_cmd(ctx: commands.Context, url: str):
    """Inspect and probe a remote CTFd platform instance without credentials."""
    cleaned_url = url.strip()
    if not cleaned_url.startswith(("http://", "https://")):
        cleaned_url = f"https://{cleaned_url}"

    # Initial outspoken status message
    status_msg = await ctx.send(
        f"🔍 **Fingerprinting target CTFd platform at** `<{cleaned_url}>`..."
    )

    # Run blocking CTFd probes in executor
    loop = bot.loop
    client = CTFdClient(cleaned_url)

    is_ctfd = await loop.run_in_executor(None, client.is_ctfd_instance)
    if not is_ctfd:
        embed = discord.Embed(
            title="❌ Target Probing Failed",
            description=f"Could not verify a valid CTFd API structure at `<{cleaned_url}>`.\n"
            "Make sure the URL points to a live CTFd instance.",
            color=discord.Color.red(),
        )
        await status_msg.edit(content=None, embed=embed)
        return

    # Fetch event title and probe endpoint status in background executor
    ctf_title = await loop.run_in_executor(None, client.get_ctf_title)
    probe_results = await loop.run_in_executor(None, client.probe_all_endpoints)

    # Build rich outspoken embed
    embed = discord.Embed(
        title=f"🎯 CTFd Instance Snapshot: {ctf_title}",
        url=client.base_url,
        description=f"**Target URL:** `{client.base_url}`\n**Fingerprint:** ✅ `CTFd API detected`",
        color=discord.Color.blue(),
    )

    endpoint_labels = {
        "users": ("👥 Users", "Registered players"),
        "teams": ("🛡️ Teams", "Competing teams"),
        "challenges": ("🧩 Challenges", "Active challenges"),
        "scoreboard": ("🏆 Scoreboard", "Live standings"),
    }

    for ep_key, (label, desc) in endpoint_labels.items():
        res = probe_results.get(ep_key, {})
        status_code = res.get("status_code", 0)

        if res.get("accessible"):
            count = res.get("count")
            count_str = f"({count} {desc.lower()})" if count is not None else ""
            val_text = f"✅ `200 OK` {count_str}"
        elif status_code in (401, 403):
            val_text = f"⚠️ `HTTP {status_code}` (Protected by admins)"
        elif status_code == 404:
            val_text = f"❌ `404 Not Found` (Disabled)"
        else:
            reason = res.get("reason", "Unavailable")
            val_text = f"❌ `{reason}`"

        embed.add_field(name=label, value=val_text, inline=True)

    embed.set_footer(text="Anonymous probe • No authentication tokens required")
    await status_msg.edit(content=None, embed=embed)


@bot.command(name="scoreboard", aliases=["standings", "lb", "leaderboard"])
async def scoreboard_cmd(ctx: commands.Context, url: str):
    """Fetch and display the live public scoreboard standings from a target CTFd instance."""
    cleaned_url = url.strip()
    if not cleaned_url.startswith(("http://", "https://")):
        cleaned_url = f"https://{cleaned_url}"

    status_msg = await ctx.send(f"🏆 **Fetching live scoreboard from** `<{cleaned_url}>`...")

    loop = bot.loop
    client = CTFdClient(cleaned_url)

    is_ctfd = await loop.run_in_executor(None, client.is_ctfd_instance)
    if not is_ctfd:
        embed = discord.Embed(
            title="❌ Scoreboard Fetch Failed",
            description=f"Could not verify a valid CTFd API structure at `<{cleaned_url}>`.",
            color=discord.Color.red(),
        )
        await status_msg.edit(content=None, embed=embed)
        return

    ctf_title = await loop.run_in_executor(None, client.get_ctf_title)
    scoreboard_data = await loop.run_in_executor(
        None, lambda: client.get_ctfd_scoreboard_details(limit=10)
    )

    if not scoreboard_data.get("accessible"):
        status_code = scoreboard_data.get("status_code", 0)
        reason = scoreboard_data.get("reason", "Protected")
        embed = discord.Embed(
            title=f"⚠️ Scoreboard Protected: {ctf_title}",
            description=f"The scoreboard endpoint is locked or hidden by administrators.\n"
            f"**Status:** `HTTP {status_code}` ({reason})",
            color=discord.Color.gold(),
        )
        await status_msg.edit(content=None, embed=embed)
        return

    standings = scoreboard_data.get("standings", [])
    if not standings:
        embed = discord.Embed(
            title=f"🏆 Live Scoreboard: {ctf_title}",
            description="The scoreboard is currently empty or no points have been scored yet.",
            color=discord.Color.blue(),
        )
        await status_msg.edit(content=None, embed=embed)
        return

    # Format standings list
    medal_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = []
    for entry in standings:
        pos = entry["pos"]
        name = entry["name"]
        score = entry["score"]
        badge = medal_emojis.get(pos, f"`#{pos:02d}`")
        lines.append(f"{badge} **{name}** — `{score} pts`")

    embed = discord.Embed(
        title=f"🏆 Live Leaderboard: {ctf_title}",
        url=f"{client.base_url}/scoreboard",
        description="\n".join(lines),
        color=discord.Color.gold(),
    )
    embed.set_footer(text="Public CTFd Standings • Top 10 Teams")
    await status_msg.edit(content=None, embed=embed)


## Reaction to messages


async def get_bot_message(payload: discord.RawReactionActionEvent) -> discord.Message | None:
    """Fetches a message from a raw reaction payload and ensures it was sent by the bot."""
    if payload.user_id == bot.user.id:
        return None

    try:
        # Resolve the channel (check cache first, then fetch via API if needed)
        channel = bot.get_channel(payload.channel_id) or await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
    except (discord.HTTPException, discord.NotFound):
        return None

    # Ensure the message belongs to the bot
    if message.author.id != bot.user.id:
        return None

    return message


@bot.event
async def on_raw_reaction_add(payload):
    """Triggers when any reaction is added to any message."""
    # Prevent the bot from responding to its own reactions
    if payload.user_id == bot.user.id:
        return

    # Extract useful information from the payload
    message_id = payload.message_id
    channel_id = payload.channel_id
    guild_id = payload.guild_id
    emoji_name = payload.emoji.name  # Returns string like '👍' or custom emoji name

    print(f"User {payload.user_id} reacted with {emoji_name} on message {message_id}")

    #
    # if the reaction is :dart: by a priviliged enough user
    if True:  # TODO if the message a is CTF link the bot has shared
        if emoji_name == "🎯":
            # Acquiring CTF as a target
            print(payload)
            message = await get_bot_message(payload)
            print(message)
            event_title = "Unknown CTF"
            if message.embeds:
                event_title = message.embeds[0].title or "Unknown CTF"

            print(f"Associated CTF Title: {event_title}")
            # TODO create a discord event, make sure not duplicated
            check_ctfd_ctf.delay("https://demo.ctfd.io/")
            print("🔄 Background sync task dispatched to Celery worker!")


# Main

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("DISCORD_TOKEN is not set in environment or .env file.")
