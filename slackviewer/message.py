from __future__ import unicode_literals

import datetime
import logging
import emoji
import re

from markupsafe import Markup
from html import unescape

class Message(object):

    _DEFAULT_USER_ICON_SIZE = 72

    def __init__(self, formatter, message, channel_id, slack_name):
        self._formatter = formatter
        self._message = message
        # default is False, we update it later if its a thread message
        self.is_thread_msg = False
        # used only with --since flag. Default to True, will update in the function
        self.is_recent_msg = True
        # Channel id is not part of self._message - at least not with slackdump
        self.channel_id = channel_id
        # slack name that is in the url https://<slackname>.slack.com
        self.slack_name = slack_name

    def __repr__(self):
        message = self._message.get("text")
        if message and len(message) > 20:
            message = message[:20] + "..."

        return f"<Message({self.username}@{self.time}: {message})>"

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
        return [ LinkAttachment("ATTACHMENT", entry, self._formatter, self)
            for entry in self._message.get("attachments", []) ]

    @property
    def files(self):
        if "file" in self._message: # this is probably an outdated case
            allfiles = [self._message["file"]]
        else:
            allfiles = self._message.get("files", [])
        return [ LinkAttachment("FILE", entry, self._formatter, self) for entry in allfiles ]

    @property
    def msg(self):
        # Slack recommends to use blocks, while the
        # 'text' field is the fall back. 'text' field also seems to be used
        # for notifications text
        #
        # There is a case where the message["text"] is much shorter as the
        # actual message. It is unclear when or why.
        # All observed messages here have been
        # done through the Slack API.
        if "blocks" in self._message and self._message["blocks"]:
            text = self._generate_blocks_text(self._message["blocks"])
        else:
            text = self._message.get("text", "")
            if not text or text.strip() == "":
                text = "[ MESSAGE TEXT EMPTY ]"
        return self._formatter.render_text(text)

    def _generate_blocks_text(self, blocks):
        """Build a message together from various message["blocks"]"""
        text = ""
        for block in blocks:
            if block["type"] == "image":
                text += self._format_block_type(block, block["type"])
            elif block["type"] in ["rich_text", "rich_text_quote"]:
                for element in block["elements"]:
                    text += self._format_rich_text_element(element)
            elif "fields" in block:
                for field in block["fields"]:
                    text += self._format_block_type(field, block["type"])
            elif "elements" in block:
                for element in block["elements"]:
                    text += self._format_block_type(element, block["type"])
            elif "type" in block and block["type"] == "divider":
                text += "---\n"
            else:
                logging.warning(f"Unknown block type: {block}")
        return text

    def _format_rich_text_element(self, element):
        """Format rich text elements based on their type and styles"""
        if element["type"] == "rich_text_quote":
            # Start the quote block
            quote_text = "<blockquote>"
            # Recursively format nested elements
            quote_text += ''.join(self._format_rich_text_element(nested_element) for nested_element in element["elements"])
            # Close the quote block
            quote_text += "</blockquote>"
            return quote_text

        elif element["type"] == "rich_text_section":
            # Recursively format nested elements
            return ''.join(self._format_rich_text_element(nested_element) for nested_element in element["elements"])

        elif element["type"] == "text":
            text = element["text"]
            if "style" in element:
                if "bold" in element["style"] and element["style"]["bold"]:
                    text = f"<b>{text}</b>"
                if "italic" in element["style"] and element["style"]["italic"]:
                    text = f"<i>{text}</i>"
            return text

        elif element["type"] == "link":
            text = element.get('text', "")
            url = element.get('url', '')

            # Unescape forward slashes in the URL
            # Slack's block kit JSON sometimes encodes forward slashes
            # as ""\\/" (a valid JSON escape). Python'sjson module may
            # leave these as literal backslash+slash depending on the serialiser,
            # so this replacement normalises them before using the URL as display text.
            url = url.replace("\\/", "/")

            if not text:
                text = url

            # Escape underscores only in display text, not in URL
            text = text.replace("_", "&#95;")

            # Escape quotes in URL for safe href attribute
            url = url.replace('"', "&quot;")

            return f'<a href="{url}">{text}</a>'

        elif element["type"] == "user":
            user = self._formatter.find_user(self.user_message(element['user_id']))
            if user:
                return f"<b>@{user.display_name}</b>"
            else:
                return f"<b>[ Unknown user {element['user_id']} ]</b>"

        elif element["type"] == "rich_text_list":
            list_text = ""
            if element["style"] == "bullet":
                list_text += "<ul>"
                list_text += "\n".join(f"<li>{self._format_rich_text_element(nested_element)}</li>" for nested_element in element["elements"])
                list_text += "</ul>\n"
            elif element["style"] == "ordered":
                list_text += "<ol>"
                list_text += "\n".join(f"<li>{self._format_rich_text_element(nested_element)}</li>" for nested_element in element["elements"])
                list_text += "</ol>\n"
            else:
                logging.warning(f"Unsupported rich text list style '{element['style']}' for {element}")
            return list_text

        elif element["type"] == "emoji":
            if "unicode" in element:
                return emoji.emojize(f":{element['name']}:", language='alias')
            else:
                return element["name"]

        # Prevent unwanted formatting of preformatted text
        elif element["type"] == "rich_text_preformatted":
            preformatted_text = ""
            for nested_element in element["elements"]:
                if nested_element["type"] == "text":
                    nested_element["text"] = nested_element["text"].replace("_", "&#95;")
                preformatted_text += self._format_rich_text_element(nested_element)
            return f"<pre>{preformatted_text}</pre>"

        elif element["type"] == "channel":
            channel_id = element["channel_id"]
            channel_name = self._formatter.find_channel(channel_id)
            if channel_name:
                return f"<a href='https://{self.slack_name}.slack.com/archives/{channel_id}'>{channel_name}</a>"
            else:
                return f"<a href='https://{self.slack_name}.slack.com/archives/{channel_id}'>[ Unknown channel {channel_id} ]</a>"

        logging.warning(f"Unsupported rich text element type '{element['type']}' for {element}")
        return ""

    def _format_block_type(self, text_obj, b_type):
        """Format the text based on the block type"""
        if b_type == "image":
            if "image_url" in text_obj:
                image_url = text_obj["image_url"]
                alt_text = text_obj.get("alt_text", "")
                title = text_obj.get("title", {}).get("text", "")
                return f"<img src='{image_url}' alt='{alt_text}' title='{title}'>\n"
            else:
                logging.warning(f"Block Type {b_type}: Missing 'image_url' in {text_obj}")
                return f"unsupported_block({b_type}: {text_obj})\n\n"

        if b_type == "context":
            if "type" in text_obj and text_obj["type"] == "image":
                if "image_url" in text_obj:
                    image_url = text_obj["image_url"]
                    alt_text = text_obj.get("alt_text", "")
                    return f"<img src='{image_url}' alt='{alt_text}'>\n"
                else:
                    logging.warning(f"Block Type {b_type}: Missing 'image_url' in {text_obj}")
                    return f"unsupported_block({b_type}: {text_obj})\n\n"
            elif "text" in text_obj:
                text = text_obj["text"]
                return f"<small>{text}</small>\n"
            else:
                logging.warning(f"Block Type {b_type}: Missing 'text' in {text_obj}")
                return f"unsupported_block({b_type}: {text_obj})\n\n"

        if "text" not in text_obj:
            logging.warning(f"Block Type {b_type}: Missing 'text' in {text_obj}")
            return f"unsupported_block({b_type}: {text_obj})\n\n"

        text = text_obj["text"]

        if "type" in text_obj and text_obj["type"] not in ["plain_text", "mrkdwn", "button"]:
            logging.warning(f"Block Type {b_type}: Unsupported text type '{text_obj['type']}' for {text_obj}")
            return f"unsupported_block({b_type}: {text})\n\n"

        if "type" in text_obj and text_obj["type"] == "button":
            if "text" in text_obj['text']:
                text = f"Slack_Button({text['text']})"

        if b_type == "header":
            return f"*{text}*\n\n"
        elif b_type == "section":
            return f"{text}\n\n"
        elif b_type == "actions":
            return f"Slack_Action({text})\n"
        else:
            logging.warning(f"Unsupported block type '{b_type}' for {text_obj}")
            return f"unsupported_block({b_type}: {text_obj}\n\n)"


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

    @property
    def permalink(self):
        permalink = f"https://{self.slack_name}.slack.com/archives/{self.channel_id}/p{self._message['ts'].replace('.','')}"
        if "thread_ts" in self._message:
            permalink += f"?thread_ts={self._message['thread_ts']}&cid={self.channel_id}"
        return permalink


class LinkAttachment():
    """
    Wrapper class for entries in either the "files" or "attachments" arrays.
    """

    _DEFAULT_THUMBNAIL_SIZE = 360

    # Fields that need to be processed for markup (and possibly markdown)
    _TEXT_FIELDS = {"pretext", "text", "footer"}

    def __init__(self, attachment_type, raw, formatter, parent_message):
        self._type = attachment_type
        self._raw = raw
        self._formatter = formatter
        self._parent_message = parent_message

    def __getitem__(self, key):
        # Check for blocks first (both message_blocks and blocks formats)
        if key == "text":
            # Check for message_blocks (nested format)
            if self._raw.get("message_blocks"):
                html_text = self._parent_message._generate_blocks_text(
                    self._raw["message_blocks"][0]["message"]["blocks"]
                )
                return Markup(html_text)

            # Check for blocks (direct format, as in your example)
            elif self._raw.get("blocks"):
                html_text = self._parent_message._generate_blocks_text(
                    self._raw["blocks"]
                )
                return Markup(html_text)

        # Process fields with emoji conversion
        if key == "fields" and self._raw.get("fields"):
            processed_fields = []
            for field in self._raw["fields"]:
                processed_field = field.copy()
                if "value" in processed_field:
                    # Convert emoji in field values
                    processed_field["value"] = self._formatter.render_text(
                        processed_field["value"],
                        process_markdown=False
                    )
                if "title" in processed_field:
                    # Also convert emoji in field titles (just in case)
                    processed_field["title"] = self._formatter.render_text(
                        processed_field["title"],
                        process_markdown=False
                    )
                processed_fields.append(processed_field)
            return processed_fields

        content = self._raw[key]
        if content and key in self._TEXT_FIELDS:
            # Always process markdown, not just when in mrkdwn_in
            content = self._formatter.render_text(content, process_markdown=True)
            # Unescape HTML entities like &rsquo;, &ldquo;, &rdquo;, &nbsp;, etc.
            content = unescape(content)
            # Prevent Jinja2 from escaping the HTML generated by render_text()
            return Markup(content)
        return content

    def get_blocks_text(self):
        """
        Generate and return text from message blocks if present in attachments.
        Returns HTML-formatted text from blocks.
        """
        if not self._raw.get("message_blocks"):
            return ""

        blocks = self._raw["message_blocks"][0]["message"]["blocks"]
        html_text = self._parent_message._generate_blocks_text(blocks)
        # Prevent Jinja2 from escaping the HTML
        return Markup(html_text)

    @property
    def blocks_text(self):
        """Property that returns the HTML-formatted text from message blocks if present."""
        return self.get_blocks_text()

    def get_rendered_blocks_text(self):
        """
        Generate and return rendered text from message blocks if present.
        Converts HTML to plain text for display.
        """
        html_text = self.get_blocks_text()
        if not html_text:
            return ""

        # Convert HTML to plain text
        plain_text = re.sub(r'<[^>]+>', '', html_text)  # Remove HTML tags
        plain_text = plain_text.replace('&nbsp;', ' ')  # Replace HTML entities
        return plain_text.strip()

    @property
    def rendered_blocks_text(self):
        """Property that returns plain text from message blocks if present."""
        return self.get_rendered_blocks_text()


    def thumbnail(self, size=None):
        """Get thumbnail information if available.

        Returns:
            dict: With 'src', 'width', and 'height' if thumbnail exists
            None: If no thumbnail is available
        """
        size = size if size else self._DEFAULT_THUMBNAIL_SIZE

        # Standard wikimedia thumbnail sizes
        #
        # Due to how common it is to link to wikipedia,
        # I expect this domain-specific improvement will be appreciated.
        # We want to check wikipedia-generated attachments to confrom to
        # thumbnail-linking standards set by https://phabricator.wikimedia.org/T414805
        STANDARD_SIZES = [20, 40, 60, 120, 250, 330, 500, 960, 1280, 1920, 3840]

        # ATTACHMENT type with direct image URL
        if "image_url" in self._raw:
            logging.debug("image_url path")
            src = self._raw["image_url"]

            # Normalize wikimedia URLs to standard thumbnail sizes
            if "wikimedia.org" in src:
                src = self._normalize_wikimedia_url(src, STANDARD_SIZES)

            return {
                "src": src,
                "width": self._raw.get("image_width"),
                "height": self._raw.get("image_height"),
            }

        # FILE type with thumbnail
        thumb_key = f"thumb_{size}"
        logging.debug("thumb path %s", thumb_key)

        # Try different thumbnail keys
        if thumb_key not in self._raw:
            thumb_key = f"thumb_{self._raw.get('filetype')}"
            if thumb_key not in self._raw:
                candidates = [k for k in self._raw.keys()
                            if k.startswith("thumb_") and not k.endswith(("_w","_h"))]
                if candidates:
                    thumb_key = candidates[0]
                    logging.info("Fell back to thumbnail key %s for [%s]",
                            thumb_key, self._raw.get("title"))

        if thumb_key in self._raw:
            return {
                "src": self._raw[thumb_key],
                "width": self._raw.get(f"{thumb_key}_w"),
                "height": self._raw.get(f"{thumb_key}_h"),
            }

        logging.info("No thumbnail found for [%s]", self._raw.get("title"))
        return None

    def _normalize_wikimedia_url(self, url, standard_sizes):
        """
        Normalize wikimedia thumbnail URLs to standard sizes.
        Replaces any px value with the closest standard size.

        Args:
            url: The wikimedia URL
            standard_sizes: List of valid thumbnail sizes

        Returns:
            Normalized URL with standard size
        """

        # Match any pixel value in the URL (e.g., "1200px-", "15px-", etc.)
        match = re.search(r'(\d+)px-', url)
        if match:
            current_px = int(match.group(1))
            # Find the closest standard size
            closest_size = min(standard_sizes, key=lambda x: abs(x - current_px))

            if closest_size != current_px:
                url = url.replace(f"{current_px}px-", f"{closest_size}px-")
                logging.info("Normalized wikimedia URL px value: %dpx → %dpx",
                            current_px, closest_size)

        return url
