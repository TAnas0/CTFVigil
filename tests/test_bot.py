"""
tests/test_bot.py
~~~~~~~~~~~~~~~~~
Unit tests for Discord bot commands and event listeners in bot.py.
All Discord API and external network interactions are mocked.
"""

from __future__ import annotations

import asyncio
import functools
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import discord
import pytest
from discord.ext import commands

import bot
from bot import (
    CLIFlags,
    ctfs_cmd,
    get_bot_message,
    hello,
    on_raw_reaction_add,
    onlinectfs_cmd,
    scoreboard_cmd,
    send_ctf_feed,
    track_cmd,
    upcoming_cmd,
    vigil_help,
)


def async_test(coro):
    """Helper runner to execute async test coroutines synchronously via asyncio.run()."""

    @functools.wraps(coro)
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))

    return wrapper


# ======================================================================= #
# Fixtures & Helpers                                                      #
# ======================================================================= #


@pytest.fixture
def mock_ctx() -> AsyncMock:
    """Create a mock discord.ext.commands.Context."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.author = MagicMock(spec=discord.Member)
    ctx.author.name = "Alice"
    ctx.author.id = 12345
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = 99999
    ctx.command = MagicMock(spec=commands.Command)
    ctx.current_parameter = None

    status_msg = AsyncMock(spec=discord.Message)
    status_msg.edit = AsyncMock()
    ctx.send = AsyncMock(return_value=status_msg)
    return ctx


@pytest.fixture
def mock_bot_user():
    """Ensure bot.bot.user is a mock user with id 999."""
    user = MagicMock(spec=discord.ClientUser)
    user.id = 999
    with patch.object(type(bot.bot), "user", new_callable=PropertyMock, return_value=user):
        yield user


@pytest.fixture
def sample_events() -> list[dict]:
    return [
        {
            "id": 1,
            "title": "Online Jeopardy 2026",
            "url": "https://jeopardy.example.com",
            "ctftime_url": "https://ctftime.org/event/1",
            "start": "2026-12-01T10:00:00Z",
            "finish": "2026-12-02T10:00:00Z",
            "format": "Jeopardy",
            "onsite": False,
            "organizers": [{"name": "CyberClub"}],
            "description": "Fun jeopardy CTF.",
        },
        {
            "id": 2,
            "title": "Onsite Attack-Defense 2026",
            "url": "https://ad.example.com",
            "ctftime_url": "https://ctftime.org/event/2",
            "start": "2026-12-05T10:00:00Z",
            "finish": "2026-12-06T10:00:00Z",
            "format": "Attack-Defense",
            "onsite": True,
            "organizers": [{"name": "UniSec"}],
            "description": "Onsite university CTF.",
        },
    ]


# ======================================================================= #
# CLIFlags Parser                                                         #
# ======================================================================= #


class TestCLIFlags:
    """Tests for CLIFlags custom flag parser."""

    @async_test
    async def test_numeric_shorthand(self, mock_ctx):
        flags = await CLIFlags.convert(mock_ctx, "10")
        assert flags.limit == 10
        assert flags.online is False

    @async_test
    async def test_flags_with_spaces_and_online(self, mock_ctx):
        flags = await CLIFlags.convert(mock_ctx, "--limit 3 --online")
        assert flags.limit == 3
        assert flags.online is True

    @async_test
    async def test_flags_with_equals_syntax(self, mock_ctx):
        flags = await CLIFlags.convert(mock_ctx, "--limit=7")
        assert flags.limit == 7
        assert flags.online is False

    @async_test
    async def test_online_flag_alone(self, mock_ctx):
        flags = await CLIFlags.convert(mock_ctx, "--online")
        assert flags.limit == 5
        assert flags.online is True


# ======================================================================= #
# Basic Commands (!hello, !vigil)                                         #
# ======================================================================= #


class TestBasicCommands:
    """Tests for !hello and !vigil command handlers."""

    @async_test
    async def test_hello_command(self, mock_ctx):
        await hello.callback(mock_ctx)
        mock_ctx.send.assert_called_once_with("Hello, Alice!")

    @async_test
    async def test_vigil_help_command(self, mock_ctx):
        await vigil_help.callback(mock_ctx)
        mock_ctx.send.assert_called_once()
        embed = mock_ctx.send.call_args[1]["embed"]
        assert isinstance(embed, discord.Embed)
        assert "Command Reference" in embed.title
        assert any("CTF Feed" in f.name for f in embed.fields)
        assert any("CTFd Platform Ops" in f.name for f in embed.fields)


# ======================================================================= #
# CTF Feed Commands                                                       #
# ======================================================================= #


class TestCTFFeedCommands:
    """Tests for feed generation and !ctfs, !upcoming, !onlinectfs."""

    @async_test
    async def test_send_ctf_feed_limit_below_one(self, mock_ctx):
        await send_ctf_feed(mock_ctx, limit=0, online=False)
        mock_ctx.send.assert_called_once_with("Please specify a limit of at least 1.")

    @async_test
    @patch.object(bot.ctf_client, "fetch_upcoming_events", new_callable=AsyncMock)
    async def test_send_ctf_feed_api_error(self, mock_fetch, mock_ctx):
        mock_fetch.side_effect = RuntimeError("CTFtime unreachable")
        await send_ctf_feed(mock_ctx, limit=5, online=False)
        mock_ctx.send.assert_called_once()
        msg = mock_ctx.send.call_args[0][0]
        assert "Error fetching CTF events" in msg

    @async_test
    @patch.object(bot.ctf_client, "fetch_upcoming_events", new_callable=AsyncMock)
    async def test_send_ctf_feed_empty_results(self, mock_fetch, mock_ctx):
        mock_fetch.return_value = []
        await send_ctf_feed(mock_ctx, limit=5, online=False)
        mock_ctx.send.assert_called_once_with("No upcoming CTFs found matching your criteria.")

    @async_test
    @patch.object(bot.ctf_client, "fetch_upcoming_events", new_callable=AsyncMock)
    async def test_send_ctf_feed_success(self, mock_fetch, mock_ctx, sample_events):
        mock_fetch.return_value = sample_events
        await send_ctf_feed(mock_ctx, limit=2, online=False)
        assert mock_ctx.send.call_count == 2
        for call_args in mock_ctx.send.call_args_list:
            embed = call_args[1].get("embed")
            assert isinstance(embed, discord.Embed)

    @async_test
    @patch.object(bot.ctf_client, "fetch_upcoming_events", new_callable=AsyncMock)
    async def test_send_ctf_feed_online_filtering(self, mock_fetch, mock_ctx, sample_events):
        mock_fetch.return_value = sample_events
        await send_ctf_feed(mock_ctx, limit=5, online=True)
        # Only 1 event is online
        assert mock_ctx.send.call_count == 1
        embed = mock_ctx.send.call_args[1]["embed"]
        assert embed.title == "Online Jeopardy 2026"

    @async_test
    @patch("bot.send_ctf_feed", new_callable=AsyncMock)
    async def test_ctfs_cmd_passes_flags(self, mock_send_feed, mock_ctx):
        flags = MagicMock(spec=CLIFlags)
        flags.limit = 4
        flags.online = True
        await ctfs_cmd.callback(mock_ctx, flags=flags)
        mock_send_feed.assert_called_once_with(mock_ctx, limit=4, online=True)

    @async_test
    @patch("bot.send_ctf_feed", new_callable=AsyncMock)
    async def test_upcoming_cmd(self, mock_send_feed, mock_ctx):
        await upcoming_cmd.callback(mock_ctx, limit=6)
        mock_send_feed.assert_called_once_with(mock_ctx, limit=6, online=False)

    @async_test
    @patch("bot.send_ctf_feed", new_callable=AsyncMock)
    async def test_onlinectfs_cmd(self, mock_send_feed, mock_ctx):
        await onlinectfs_cmd.callback(mock_ctx, limit=3)
        mock_send_feed.assert_called_once_with(mock_ctx, limit=3, online=True)


# ======================================================================= #
# CTFd Ops Commands (!track, !scoreboard)                                 #
# ======================================================================= #


class TestTrackCommand:
    """Tests for !track command."""

    @async_test
    @patch("bot.CTFdClient")
    async def test_track_invalid_ctfd(self, mock_client_cls, mock_ctx):
        mock_client = MagicMock()
        mock_client.is_ctfd_instance.return_value = False
        mock_client_cls.return_value = mock_client

        status_msg = mock_ctx.send.return_value
        await track_cmd.callback(mock_ctx, "https://not-ctfd.com")

        status_msg.edit.assert_called_once()
        embed = status_msg.edit.call_args[1]["embed"]
        assert "Target Probing Failed" in embed.title

    @async_test
    @patch("bot.CTFdClient")
    async def test_track_valid_ctfd(self, mock_client_cls, mock_ctx):
        mock_client = MagicMock()
        mock_client.is_ctfd_instance.return_value = True
        mock_client.get_ctf_title.return_value = "CyberFest 2026"
        mock_client.base_url = "https://demo.ctfd.io"
        mock_client.probe_all_endpoints.return_value = {
            "users": {"accessible": True, "count": 120, "status_code": 200},
            "teams": {"accessible": True, "count": 35, "status_code": 200},
            "challenges": {"accessible": False, "status_code": 403, "reason": "Protected"},
            "scoreboard": {"accessible": True, "count": 35, "status_code": 200},
        }
        mock_client_cls.return_value = mock_client

        status_msg = mock_ctx.send.return_value
        await track_cmd.callback(mock_ctx, "demo.ctfd.io")

        status_msg.edit.assert_called_once()
        embed = status_msg.edit.call_args[1]["embed"]
        assert "CyberFest 2026" in embed.title
        assert len(embed.fields) == 4


class TestScoreboardCommand:
    """Tests for !scoreboard command."""

    @async_test
    @patch("bot.CTFdClient")
    async def test_scoreboard_not_ctfd(self, mock_client_cls, mock_ctx):
        mock_client = MagicMock()
        mock_client.is_ctfd_instance.return_value = False
        mock_client_cls.return_value = mock_client

        status_msg = mock_ctx.send.return_value
        await scoreboard_cmd.callback(mock_ctx, "https://invalid.com")

        embed = status_msg.edit.call_args[1]["embed"]
        assert "Scoreboard Fetch Failed" in embed.title

    @async_test
    @patch("bot.CTFdClient")
    async def test_scoreboard_protected(self, mock_client_cls, mock_ctx):
        mock_client = MagicMock()
        mock_client.is_ctfd_instance.return_value = True
        mock_client.get_ctf_title.return_value = "SecCTF"
        mock_client.get_ctfd_scoreboard_details.return_value = {
            "accessible": False,
            "status_code": 403,
            "reason": "Forbidden",
            "standings": [],
        }
        mock_client_cls.return_value = mock_client

        status_msg = mock_ctx.send.return_value
        await scoreboard_cmd.callback(mock_ctx, "https://demo.ctfd.io")

        embed = status_msg.edit.call_args[1]["embed"]
        assert "Scoreboard Protected" in embed.title

    @async_test
    @patch("bot.CTFdClient")
    async def test_scoreboard_empty(self, mock_client_cls, mock_ctx):
        mock_client = MagicMock()
        mock_client.is_ctfd_instance.return_value = True
        mock_client.get_ctf_title.return_value = "EmptyCTF"
        mock_client.get_ctfd_scoreboard_details.return_value = {
            "accessible": True,
            "status_code": 200,
            "standings": [],
        }
        mock_client_cls.return_value = mock_client

        status_msg = mock_ctx.send.return_value
        await scoreboard_cmd.callback(mock_ctx, "https://demo.ctfd.io")

        embed = status_msg.edit.call_args[1]["embed"]
        assert "Live Scoreboard" in embed.title
        assert "empty" in embed.description

    @async_test
    @patch("bot.CTFdClient")
    async def test_scoreboard_success(self, mock_client_cls, mock_ctx):
        mock_client = MagicMock()
        mock_client.is_ctfd_instance.return_value = True
        mock_client.get_ctf_title.return_value = "LiveCTF"
        mock_client.base_url = "https://demo.ctfd.io"
        mock_client.get_ctfd_scoreboard_details.return_value = {
            "accessible": True,
            "status_code": 200,
            "standings": [
                {"pos": 1, "name": "Team Alpha", "score": 2500},
                {"pos": 2, "name": "Team Beta", "score": 1900},
            ],
        }
        mock_client_cls.return_value = mock_client

        status_msg = mock_ctx.send.return_value
        await scoreboard_cmd.callback(mock_ctx, "https://demo.ctfd.io")

        embed = status_msg.edit.call_args[1]["embed"]
        assert "Live Leaderboard" in embed.title
        assert "🥇 **Team Alpha**" in embed.description
        assert "🥈 **Team Beta**" in embed.description


# ======================================================================= #
# Reaction Events & get_bot_message                                       #
# ======================================================================= #


class TestReactionHandler:
    """Tests for on_raw_reaction_add and get_bot_message."""

    @async_test
    async def test_ignores_reaction_from_bot_itself(self, mock_bot_user):
        payload = MagicMock(spec=discord.RawReactionActionEvent)
        payload.user_id = 999
        with patch("bot.get_bot_message", new_callable=AsyncMock) as mock_get_msg:
            await on_raw_reaction_add(payload)
            mock_get_msg.assert_not_called()

    @async_test
    async def test_ignores_non_target_emoji(self, mock_bot_user):
        payload = MagicMock(spec=discord.RawReactionActionEvent)
        payload.user_id = 111
        payload.emoji.name = "👍"
        with patch("bot.get_bot_message", new_callable=AsyncMock) as mock_get_msg:
            await on_raw_reaction_add(payload)
            mock_get_msg.assert_not_called()

    @async_test
    @patch("bot.check_ctfd_ctf.delay")
    async def test_target_acquired_with_direct_embed_url(self, mock_delay, mock_bot_user):
        payload = MagicMock(spec=discord.RawReactionActionEvent)
        payload.user_id = 111
        payload.emoji.name = "🎯"

        mock_msg = MagicMock(spec=discord.Message)
        embed = discord.Embed(title="Target CTF", url="https://target.ctf.io")
        mock_msg.embeds = [embed]

        with patch("bot.get_bot_message", new_callable=AsyncMock, return_value=mock_msg):
            await on_raw_reaction_add(payload)
            mock_delay.assert_called_once_with("https://target.ctf.io")

    @async_test
    @patch("bot.check_ctfd_ctf.delay")
    async def test_target_acquired_with_ctftime_field_fallback(self, mock_delay, mock_bot_user):
        payload = MagicMock(spec=discord.RawReactionActionEvent)
        payload.user_id = 111
        payload.emoji.name = "🎯"

        mock_msg = MagicMock(spec=discord.Message)
        embed = discord.Embed(title="Target CTF")
        embed.url = None
        embed.add_field(name="🔗 CTFtime", value="[Event Page](https://ctftime.org/event/999)")
        mock_msg.embeds = [embed]

        with patch("bot.get_bot_message", new_callable=AsyncMock, return_value=mock_msg):
            await on_raw_reaction_add(payload)
            mock_delay.assert_called_once_with("https://ctftime.org/event/999")

    @async_test
    @patch("bot.check_ctfd_ctf.delay")
    async def test_target_acquired_message_none_handled(self, mock_delay, mock_bot_user):
        payload = MagicMock(spec=discord.RawReactionActionEvent)
        payload.user_id = 111
        payload.emoji.name = "🎯"

        with patch("bot.get_bot_message", new_callable=AsyncMock, return_value=None):
            await on_raw_reaction_add(payload)
            mock_delay.assert_not_called()

    @async_test
    async def test_get_bot_message_ignores_different_author(self, mock_bot_user):
        payload = MagicMock(spec=discord.RawReactionActionEvent)
        payload.user_id = 111
        payload.channel_id = 222
        payload.message_id = 333

        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_msg = AsyncMock(spec=discord.Message)
        mock_msg.author.id = 555  # Different from bot id 999
        mock_channel.fetch_message.return_value = mock_msg

        with patch.object(bot.bot, "get_channel", return_value=mock_channel):
            res = await get_bot_message(payload)
            assert res is None

    @async_test
    async def test_get_bot_message_not_found_returns_none(self, mock_bot_user):
        payload = MagicMock(spec=discord.RawReactionActionEvent)
        payload.user_id = 111
        payload.channel_id = 222
        payload.message_id = 333

        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_channel.fetch_message.side_effect = discord.NotFound(
            response=MagicMock(status=404), message="Not Found"
        )

        with patch.object(bot.bot, "get_channel", return_value=mock_channel):
            res = await get_bot_message(payload)
            assert res is None
