from __future__ import unicode_literals

import datetime
import logging
import emoji

class Message(object):

    _DEFAULT_USER_ICON_SIZE = 72

    def __init__(self, formatter, message):
        self._formatter = formatter
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
            elif "user" in self._message:
                return self.user_id
            elif "bot_id" in self._message:
                return self._message["bot_id"]
            else:
                return None

    @property
    def time(self):
        # Check if 'ts' key exists in the dictionary
        if "ts" in self._message:
            # Handle this: "ts": "1456427378.000002"
            tsepoch = float(self._message["ts"].split(".")[0])
            return str(datetime.datetime.fromtimestamp(tsepoch)).split('.')[0]
        else:
            return None  # or return a suitable default value

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

    def user_message(self, user_id):
       return {"user": user_id}

    def usernames(self, reaction):
        return [
            self._formatter.find_user(self.user_message(user_id)).display_name
            for user_id
            in reaction.get("users")
            if self._formatter.find_user(self.user_message(user_id))
        ]

    @property
    def reactions(self):
        reactions = self._message.get("reactions", [])
        return [
            {
                "usernames": self.usernames(reaction),
                "name": emoji.emojize(
                    self._formatter.slack_to_accepted_emoji(':{}:'.format(reaction.get("name"))),
                    language='alias'
                )
            }
            for reaction in reactions
        ]

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
        """
        Fetch the "fields" list, and process the text within each field, including markdown
        processing if the message indicates that the fields contain markdown.

        Only present on attachments, not files--this abstraction isn't 100% awesome.'
        """
        process_markdown = ("fields" in self._raw.get("mrkdwn_in", []))
        fields = self._raw.get("fields", [])
        if fields:
            logging.debug("Rendering with markdown markdown %s for %s", process_markdown, fields)
        return [
            {"title": e["title"], "short": e.get("short", False), "value": self._formatter.render_text(e["value"], process_markdown)}
            for e in fields
        ]
