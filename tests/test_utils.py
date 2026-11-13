from datetime import datetime, timezone
import pytest
import discord

from ctfvigil.utils import create_event_embed, format_description, iso_to_timestamp


class TestIsoToTimestamp:
    """Tests for iso_to_timestamp utility function."""

    def test_valid_iso_utc_with_z(self):
        iso_str = "2026-08-30T12:00:00Z"
        expected = int(datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc).timestamp())
        assert iso_to_timestamp(iso_str) == expected

    def test_valid_iso_with_explicit_offset(self):
        iso_str = "2026-08-30T14:00:00+02:00"
        expected = int(datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc).timestamp())
        assert iso_to_timestamp(iso_str) == expected

    def test_valid_iso_negative_offset(self):
        iso_str = "2026-08-30T07:00:00-05:00"
        expected = int(datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc).timestamp())
        assert iso_to_timestamp(iso_str) == expected

    def test_valid_iso_without_timezone_naive(self):
        iso_str = "2026-08-30T12:00:00"
        dt = datetime.fromisoformat(iso_str)
        assert iso_to_timestamp(iso_str) == int(dt.timestamp())

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "",
            None,
            "invalid-date-string",
            "2026-99-99T99:99:99Z",
            "12345",
            [],
            {},
        ],
    )
    def test_falsy_or_invalid_iso_strings(self, invalid_input):
        assert iso_to_timestamp(invalid_input) is None

    def test_non_string_non_falsy_raises_attribute_error(self):
        with pytest.raises(AttributeError):
            iso_to_timestamp(12345)


class TestFormatDescription:
    """Tests for format_description utility function."""

    def test_none_or_empty_input(self):
        assert format_description(None) == "No description provided."
        assert format_description("") == "No description provided."
        assert format_description("   \n\n\t ") == "No description provided."

    def test_single_paragraph_without_trailing_period(self):
        desc = "Welcome to CTFVigil"
        assert format_description(desc) == "Welcome to CTFVigil..."

    def test_single_paragraph_with_trailing_period_and_spaces(self):
        desc = "Welcome to CTFVigil.   "
        assert format_description(desc) == "Welcome to CTFVigil..."

    def test_multiple_paragraphs_separated_by_newlines(self):
        desc = "First paragraph content.\n\nSecond paragraph content.\nThird paragraph."
        assert format_description(desc) == "First paragraph content..."

    def test_multiple_paragraphs_separated_by_windows_newlines(self):
        desc = "First paragraph content.\r\n  \r\nSecond paragraph content."
        assert format_description(desc) == "First paragraph content..."

    def test_paragraph_with_internal_newlines(self):
        desc = "First line of paragraph 1.\nSecond line of paragraph 1.\n\nParagraph 2."
        assert (
            format_description(desc) == "First line of paragraph 1.\nSecond line of paragraph 1..."
        )

    def test_leading_and_trailing_whitespace(self):
        desc = "\n\n  This is a padded description.  \n\n  Other text.  "
        assert format_description(desc) == "This is a padded description..."


class TestCreateEventEmbed:
    """Tests for create_event_embed utility function."""

    @pytest.fixture
    def full_event_data(self):
        return {
            "title": "SuperCTF 2026",
            "url": "https://superctf.example.com",
            "ctftime_url": "https://ctftime.org/event/1234",
            "format": "Jeopardy",
            "onsite": False,
            "organizers": [{"name": "Security Guild"}],
            "start": "2026-09-01T12:00:00Z",
            "finish": "2026-09-03T12:00:00Z",
            "description": "The ultimate CTF competition.\n\nPrize pool details...",
        }

    def test_create_embed_with_complete_data(self, full_event_data):
        embed = create_event_embed(full_event_data)

        assert isinstance(embed, discord.Embed)
        assert embed.title == "SuperCTF 2026"
        assert embed.url == "https://superctf.example.com"
        assert embed.description == "The ultimate CTF competition..."
        assert embed.color == discord.Color.dark_purple()

        # Check embed fields
        fields_dict = {field.name: field.value for field in embed.fields}

        start_ts = iso_to_timestamp("2026-09-01T12:00:00Z")
        finish_ts = iso_to_timestamp("2026-09-03T12:00:00Z")

        assert fields_dict["⏰ Starts"] == f"<t:{start_ts}:F>\n(<t:{start_ts}:R>)"
        assert fields_dict["⏳ Ends"] == f"<t:{finish_ts}:F>\n(<t:{finish_ts}:R>)"
        assert fields_dict["🏛️ Organizer"] == "Security Guild"
        assert fields_dict["🏆 Format"] == "Jeopardy (Online)"
        assert fields_dict["🔗 CTFtime"] == "[Event Page](https://ctftime.org/event/1234)"

    def test_create_embed_with_minimal_data(self):
        embed = create_event_embed({})

        assert embed.title == "Unnamed CTF"
        assert embed.url is None or embed.url == ""
        assert embed.description == "No description provided."

        fields_dict = {field.name: field.value for field in embed.fields}

        assert "⏰ Starts" not in fields_dict
        assert "⏳ Ends" not in fields_dict
        assert fields_dict["🏛️ Organizer"] == "Unknown"
        assert fields_dict["🏆 Format"] == "Unknown (Online)"
        assert "🔗 CTFtime" not in fields_dict

    def test_fallback_url_to_ctftime_link(self):
        event = {
            "ctftime_url": "https://ctftime.org/event/9999",
            "url": "",  # Empty URL string should fall back to ctftime_url
        }
        embed = create_event_embed(event)
        assert embed.url == "https://ctftime.org/event/9999"

    def test_onsite_location_formatting(self):
        event = {"onsite": True}
        embed = create_event_embed(event)
        fields_dict = {field.name: field.value for field in embed.fields}
        assert fields_dict["🏆 Format"] == "Unknown (On-Site)"

    def test_empty_organizers_list(self):
        event = {"organizers": []}
        embed = create_event_embed(event)
        fields_dict = {field.name: field.value for field in embed.fields}
        assert fields_dict["🏛️ Organizer"] == "Unknown"
