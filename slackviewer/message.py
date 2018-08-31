from __future__ import unicode_literals

import datetime
import logging
import re

import emoji
import markdown2
from slackviewer.user import User


class Message(object):

    _DEFAULT_USER_ICON_SIZE = 72

    def __init__(self, USER_DATA, CHANNEL_DATA, message):
        self._formatter = SlackFormatter(USER_DATA, CHANNEL_DATA)
        self._message = message

    ##############
    # Properties #
    ##############

    @property
    def user_id(self):
        if "user" in self._message:
            return self._message["user"]
        elif "bot_id" in self._message:
            return self._message["bot_id"]
        else:
            logging.error("No user ID on %s", self._message)


    @property
    def user(self):
        return self._formatter.find_user(self._message)

    @property
    def username(self):
        try:
            return self.user.display_name
        except KeyError:
            # In case this is a bot or something, we fallback to "username"
            if "username" in self._message:
                return self._message["username"]
            # If that fails to, it's probably USLACKBOT...
            if "user" in self._message:
                if self.user_id == "USLACKBOT":
                    return "slackbot"
                else:
                    return self.user_id
            elif "bot_id" in self._message:
                return self._message["bot_id"]
            else:
                return None

    @property
    def time(self):
        # Handle this: "ts": "1456427378.000002"
        tsepoch = float(self._message["ts"].split(".")[0])
        return str(datetime.datetime.fromtimestamp(tsepoch)).split('.')[0]

    @property
    def attachments(self):
        return [ LinkAttachment("ATTACHMENT", entry, self._formatter)
            for entry in self._message.get("attachments", []) ]

    @property
    def files(self):
        if "file" in self._message: # this is probably an outdated case
            allfiles = [self._message["file"]]
        else:
            allfiles = self._message.get("files", [])
        return [ LinkAttachment("FILE", entry, self._formatter) for entry in allfiles ]

    @property
    def msg(self):
        text = self._message.get("text")
        if text:
            text = self._formatter.render_text(text)
        return text

    @property
    def img(self):
        try:
            return self.user.image_url(self._DEFAULT_USER_ICON_SIZE)
        except KeyError:
            return ""

    @property
    def id(self):
        return self.time

    @property
    def subtype(self):
        return self._message.get("subtype")


class SlackFormatter(object):
    "This formats messages and provides access to workspace-wide data (user and channel metadata)."

    # Class-level constants for precompilation of frequently-reused regular expressions
    # URL detection relies on http://stackoverflow.com/a/1547940/1798683
    _LINK_PAT = re.compile(r"<(https|http|mailto):[A-Za-z0-9_\.\-\/\?\,\=\#\:\@]+\|[^>]+>")
    _MENTION_PAT = re.compile(r"<((?:#C|@[UB])\w+)(?:\|([A-Za-z0-9.-_]+))?>")
    _HASHTAG_PAT = re.compile(r"(^| )#[A-Za-z][\w\.\-\_]+( |$)")

    def __init__(self, USER_DATA, CHANNEL_DATA):
        self.__USER_DATA = USER_DATA
        self.__CHANNEL_DATA = CHANNEL_DATA

    def find_user(self, message):
        if message.get("user") == "USLACKBOT":
            return User({"name":"slackbot"})
        if message.get("subtype", "").startswith("bot_") and message["bot_id"] not in self.__USER_DATA:
            bot_id = message["bot_id"]
            logging.debug("bot addition for %s", bot_id)
            if "bot_link" in message:
                (bot_url, bot_name) = message["bot_link"].strip("<>").split("|", 1)
            elif "username" in message:
                bot_name = message["username"]
                bot_url = None

            self.__USER_DATA[bot_id] = User({
                "user": bot_id,
                "real_name": bot_name,
                "bot_url": bot_url,
                "is_bot": True,
                "is_app_user": True
            })
        user_id = message.get("user") or message.get("bot_id")
        if user_id in self.__USER_DATA:
            return self.__USER_DATA.get(user_id)
        logging.error("unable to find user in %s", message)

    def render_text(self, message, process_markdown=True):
        message = message.replace("<!channel>", "@channel")
        message = self._slack_to_accepted_emoji(message)

        # Handle mentions of users, channels and bots (e.g "<@U0BM1CGQY|calvinchanubc> has joined the channel")
        message = self._MENTION_PAT.sub(self._sub_annotated_mention, message)
        # Handle links
        message = self._LINK_PAT.sub(self._sub_hyperlink, message)
        # Handle hashtags (that are meant to be hashtags and not headings)
        message = self._HASHTAG_PAT.sub(self._sub_hashtag, message)

        # Introduce unicode emoji
        message = emoji.emojize(message, use_aliases=True)

        if process_markdown:
            # Handle bold (convert * * to ** **)
            message = re.sub(r'\*', "**", message)

            message = markdown2.markdown(
                message,
                extras=[
                    "cuddled-lists",
                    # This gives us <pre> and <code> tags for ```-fenced blocks
                    "fenced-code-blocks",
                    "pyshell"
                ]
            ).strip()

        # Special handling cases for lists
        message = message.replace("\n\n<ul>", "<ul>")
        message = message.replace("\n<li>", "<li>")

        return message

    def _slack_to_accepted_emoji(self, message):
        # https://github.com/Ranks/emojione/issues/114
        message = message.replace(":simple_smile:", ":slightly_smiling_face:")
        return message

    def _sub_annotated_mention(self, matchobj):
        ref_id = matchobj.group(1)[1:]  # drop #/@ from the start, we don't care
        annotation = matchobj.group(2)
        if ref_id.startswith('C'):
            mention_format = "<b>#{}</b>"
            if not annotation:
                channel = self.__CHANNEL_DATA.get(ref_id)
                annotation = channel["name"] if channel else ref_id
        else:
            mention_format = "@{}"
            if not annotation:
                user = self.__USER_DATA.get(ref_id)
                annotation = user.display_name if user else ref_id
        return mention_format.format(annotation)

    def _sub_hyperlink(self, matchobj):
        compound = matchobj.group(0)[1:-1]
        if len(compound.split("|")) == 2:
            url, title = compound.split("|")
        else:
            url, title = compound, compound
        result = "<a href=\"{url}\">{title}</a>".format(url=url, title=title)
        return result

    def _sub_hashtag(self, matchobj):
        text = matchobj.group(0)

        starting_space = " " if text[0] == " " else ""
        ending_space = " " if text[-1] == " " else ""

        return "{}<b>{}</b>{}".format(
            starting_space,
            text.strip(),
            ending_space
        )


class LinkAttachment(object):
    """
    Wrapper class for entries in either the "files" or "attachments" arrays.
    """

    _DEFAULT_THUMBNAIL_SIZE = 360

    # Fields that need to be processed for markup (and possibly markdown)
    _TEXT_FIELDS = {"pretext", "text", "footer"}

    def __init__(self, attachment_type, raw, formatter):
        self._type = attachment_type
        self._raw = raw
        self._formatter = formatter

    def __getitem__(self, key):
        content = self._raw[key]
        if content and key in self._TEXT_FIELDS:
            process_markdown = (key in self._raw.get("mrkdwn_in", []))
            content = self._formatter.render_text(content, process_markdown)
        return content

    def thumbnail(self, size=None):
        size = size if size else self._DEFAULT_THUMBNAIL_SIZE
        # ATTACHMENT type
        if "image_url" in self._raw:
            logging.debug("image_url path")
            return {
                "src": self._raw["image_url"],
                "width": self._raw.get("image_width"),
                "height": self._raw.get("image_height"),
            }
        else: # FILE type
            thumb_key = "thumb_{}".format(size)
            logging.debug("thumb path" + thumb_key)
            if thumb_key not in self._raw:
                # let's try some fallback logic
                thumb_key = "thumb_{}".format(self._raw.get("filetype"))
                if thumb_key not in self._raw:
                    # pick the first one that shows up in the iterator
                    candidates = [k for k in self._raw.keys()
                        if k.startswith("thumb_") and not k.endswith(("_w","_h"))]
                    if candidates:
                        thumb_key = candidates[0]
                        logging.info("Fell back to thumbnail key %s for [%s]",
                            thumb_key, self._raw.get("title"))
            if thumb_key in self._raw:
                return {
                    "src": self._raw[thumb_key],
                    "width": self._raw.get(thumb_key + "_w"),
                    "height": self._raw.get(thumb_key + "_h"),
                }
            else:
                logging.info("No thumbnail found for [%s]", self._raw.get("title"))

    @property
    def is_image(self):
        return self._raw.get("mimetype", "").startswith("image/")

    @property
    def link(self):
        if "from_url" in self._raw:
            return self._raw["from_url"]
        else:
            return self._raw.get("url_private")

    @property
    def fields(self):
        "Only present on attachments, not files--this abstraction isn't 100% awesome.'"
        process_markdown = ("fields" in self._raw.get("mrkdwn_in", []))
        fields = self._raw.get("fields", [])
        if fields:
            logging.debug("Rendering with markdown markdown %s for %s", process_markdown, fields)
        return [
            {"title": e["title"], "short": e["short"], "value": self._formatter.render_text(e["value"], process_markdown)}
            for e in fields
        ]
