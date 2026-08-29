import re
from datetime import datetime

import discord


def iso_to_timestamp(iso_str: str | None) -> int | None:
    """Convert an ISO 8601 timestamp string to a Unix timestamp integer."""
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except (ValueError, TypeError):
        return None


def format_description(desc: str | None) -> str:
    """Truncate a description to its first paragraph, ending with '...'."""
    if not desc:
        return "No description provided."
    paragraphs = [p.strip() for p in re.split(r"\r?\n\s*\r?\n", desc.strip()) if p.strip()]
    if not paragraphs:
        return "No description provided."
    return paragraphs[0].rstrip(". ") + "..."


def create_event_embed(event: dict) -> discord.Embed:
    """Build a compact Discord embed for a CTF event (no thumbnails or images)."""
    name = event.get("title", "Unnamed CTF")
    ctftime_link = event.get("ctftime_url", "")
    event_url = event.get("url") or ctftime_link
    format_type = event.get("format", "Unknown")
    location_str = "On-Site" if event.get("onsite", False) else "Online"

    orgs = event.get("organizers", [])
    org_name = orgs[0].get("name") if orgs else "Unknown"

    start_ts = iso_to_timestamp(event.get("start"))
    finish_ts = iso_to_timestamp(event.get("finish"))

    embed = discord.Embed(
        title=name,
        url=event_url,
        description=format_description(event.get("description")),
        color=discord.Color.dark_purple(),
    )

    if start_ts:
        embed.add_field(name="⏰ Starts", value=f"<t:{start_ts}:F>\n(<t:{start_ts}:R>)", inline=True)
    if finish_ts:
        embed.add_field(name="⏳ Ends", value=f"<t:{finish_ts}:F>\n(<t:{finish_ts}:R>)", inline=True)

    embed.add_field(name="🏛️ Organizer", value=org_name, inline=True)
    embed.add_field(name="🏆 Format", value=f"{format_type} ({location_str})", inline=True)
    if ctftime_link:
        embed.add_field(name="🔗 CTFtime", value=f"[Event Page]({ctftime_link})", inline=True)

    return embed
