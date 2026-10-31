import datetime
from types import SimpleNamespace

from slackviewer.formatter import SlackFormatter
from slackviewer.message import Message
from slackviewer.reader import Reader


def make_message(**fields):
    for key in ("ts", "thread_ts"):
        if key in fields:
            fields[key] = str(fields[key])
    return Message(SlackFormatter({}, {}), fields, "C1", "test")


def build_threads(messages, since=None, skip_channel_member_change=False):
    reader = Reader.__new__(Reader)
    reader._config = SimpleNamespace(
        skip_channel_member_change=skip_channel_member_change,
        thread_note=False,
    )
    reader._since = since
    return reader._build_threads({"general": messages})


def layout(channel_data):
    """(ts, is_thread_msg) for each message in the channel"""
    return [(m._message["ts"], m.is_thread_msg) for m in channel_data["general"]]


def test_threads_without_replies_array():
    channel = build_threads([
        make_message(user="U1", ts=200, thread_ts=200, reply_count=2),
        make_message(user="U2", ts=201, thread_ts=200),
        make_message(user="U3", ts=202, thread_ts=200),
    ])
    assert layout(channel) == [("200", False), ("201", True), ("202", True)]


def test_threads_bot_reply():
    channel = build_threads([
        make_message(user="U1", ts=600, thread_ts=600, reply_count=1),
        make_message(bot_id="B1", ts=602, thread_ts=600),
    ])
    assert layout(channel) == [("600", False), ("602", True)]


def test_threads_replies_are_chronological_and_not_duplicated():
    channel = build_threads([
        make_message(user="U1", ts=100, thread_ts=100,
                     replies=[{"user": "U2", "ts": "101"}, {"user": "W9", "ts": "103"}, {"user": "U1"}]),
        make_message(user="U2", ts=101, thread_ts=100),
        make_message(user="U3", ts=102, thread_ts=100),
        make_message(user="U3", ts=103, thread_ts=100),
        make_message(user="U2", ts=104, thread_ts=100),
        make_message(user="U4", ts=105),
    ])
    assert layout(channel) == [
        ("100", False), ("101", True), ("102", True), ("103", True), ("104", True), ("105", False),
    ]


def test_threads_message_without_ts():
    messages = [
        make_message(user="U1", ts=800, thread_ts=800),
        make_message(user="U2", thread_ts=800),
    ]
    channel = build_threads(messages)
    assert channel["general"] == messages
    assert not messages[1].is_thread_msg


def test_threads_reply_to_skipped_channel_join():
    channel = build_threads([
        make_message(user="U1", ts=700, thread_ts=700, subtype="channel_join"),
        make_message(user="U2", ts=701, thread_ts=700),
    ], skip_channel_member_change=True)
    assert layout(channel) == [("701", False)]


def test_threads_since_keeps_thread_with_recent_reply():
    channel = build_threads([
        make_message(user="U1", ts=500, thread_ts=500),
        make_message(user="U3", ts=501, thread_ts=500),
        make_message(user="U2", ts=503, thread_ts=500),
    ], since=datetime.datetime.fromtimestamp(502))
    assert layout(channel) == [("500", False), ("501", True), ("503", True)]
    assert [m.is_recent_msg for m in channel["general"]] == [False, False, True]


def render_link(url, text=None):
    element = {"type": "link", "url": url}
    if text is not None:
        element["text"] = text
    blocks = [{"type": "rich_text", "elements": [{"type": "rich_text_section", "elements": [element]}]}]
    return make_message(ts=1, blocks=blocks).msg


def test_link_asterisks_are_not_bold():
    html = render_link("https://ex.com/p*q*r")
    assert "<strong>" not in html
    assert 'href="https://ex.com/p&#42;q&#42;r"' in html


def test_link_unsafe_scheme_is_not_linked():
    html = render_link("javascript:alert(1)", "click")
    assert "<a" not in html
    assert "javascript" not in html


def test_link_label_is_escaped():
    html = render_link("https://ex.com/?a=1&b=2", "<img src=x onerror=alert(1)>")
    assert "<img" not in html
    assert 'href="https://ex.com/?a=1&amp;b=2"' in html
