from collections import OrderedDict

import glob
import io
import json
import os
import datetime
import logging
import pathlib

from slackviewer.formatter import SlackFormatter
from slackviewer.message import Message
from slackviewer.user import User, deleted_user
from slackviewer.archive import extract_archive


class Reader(object):
    """
    Reader object will read all of the archives' data from the json files
    """

    def __init__(self, config):
        self._config = config
        self._PATH = extract_archive(config.archive)
        self._since = config.since

        # keep list of all channels to hide to flag not found ones
        self._remaining_unhidden_channels = config.hide_channels.copy()

        # slack name that is in the url https://<slackname>.slack.com
        self._slack_name = self._get_slack_name()

        self.filter_user_attribute = None
        self.filter_user_value = None
        if config.filter_user:
            if ":" not in config.filter_user:
                raise ValueError("Invalid filter_user format. Use <attribute:value>")
            self.filter_user_attribute, self.filter_user_value = config.filter_user.split(":", 1)

        # TODO: Make sure this works

        users_file = os.path.join(self._PATH, "users.json")
        if not os.path.exists(users_file):
            enterprise_users_file = os.path.join(self._PATH, "org_users.json")
            if os.path.exists(enterprise_users_file):
                users_file = enterprise_users_file
            else:
                logging.warning(f"Neither 'users.json' nor 'org_users.json' was found at {self._PATH}. Is this file not present or in the wrong location?")

        with io.open(users_file, encoding="utf8") as f:
            self.__USER_DATA = {u["id"]: User(u) for u in json.load(f)}
            slackbot = {
                "id": "USLACKBOT",
                "name": "slackbot",
                "profile": {
                    "image_24": "https://a.slack-edge.com/0180/img/slackbot_24.png",
                    "image_32": "https://a.slack-edge.com/2fac/plugins/slackbot/assets/service_32.png",
                    "image_48": "https://a.slack-edge.com/2fac/plugins/slackbot/assets/service_48.png",
                    "image_72": "https://a.slack-edge.com/0180/img/slackbot_72.png",
                    "image_192": "https://a.slack-edge.com/66f9/img/slackbot_192.png",
                    "image_512": "https://a.slack-edge.com/1801/img/slackbot_512.png",
                }
            }
            self.__USER_DATA.setdefault("USLACKBOT", User(slackbot))

    ##################
    # Public Methods #
    ##################

    def compile_channels(self, channels=None):
        if isinstance(channels, str):
            channels = channels.split(',')

        channel_data = self._read_from_json("channels.json")
        channel_names = [c["name"] for c in channel_data.values() if not channels or c["name"] in channels]

        channel_names = self._remove_hidden_channels(channel_names)

        return self._create_messages(channel_names, channel_data)

    def compile_groups(self):
        """Get private channels"""

        group_data = self._read_from_json("groups.json")
        group_names = [c["name"] for c in group_data.values()]

        group_names = self._remove_hidden_channels(group_names)

        return self._create_messages(group_names, group_data)

    def compile_dm_messages(self):
        # Gets list of dm objects with dm ID and array of members ids
        dm_data = self._read_from_json("dms.json")
        dm_ids = [c["id"] for c in dm_data.values()]

        # True is passed here to let the create messages function know that
        # it is dm data being passed to it
        return self._create_messages(dm_ids, dm_data, True)

    def compile_dm_users(self):
        """
        Gets the info for the members within the dm

        Returns a list of all dms with the members that have ever existed

        :rtype: [object]
        {
            id: <id>
            users: [<user_id>]
        }

        """

        dm_data = self._read_from_json("dms.json")
        dms = dm_data.values()
        all_dms_users = []

        for dm in dms:
            # checks if messages actually exist
            if dm["id"] not in self._EMPTY_DMS:
                # added try catch for users from shared workspaces not in current workspace
                try:
                    if "members" in dm:
                        users = dm["members"]
                    if "user" in dm:
                        users = [dm["user"]]
                    dm_members = {"id": dm["id"], "users": [self.__USER_DATA.setdefault(m, deleted_user(m)) for m in users]}
                    all_dms_users.append(dm_members)
                except KeyError:
                    dm_members = None

        return all_dms_users

    def compile_mpim_messages(self):
        """Return multiple person DM groups"""

        mpim_data = self._read_from_json("mpims.json")
        mpim_names = [c["name"] for c in mpim_data.values()]

        return self._create_messages(mpim_names, mpim_data)

    def compile_mpim_users(self):
        """
        Gets the info for the members within the multiple person instant message

        Returns a list of all dms with the members that have ever existed

        :rtype: [object]
        {
            name: <name>
            users: [<user_id>]
        }

        """

        mpim_data = self._read_from_json("mpims.json")
        mpims = [c for c in mpim_data.values()]
        all_mpim_users = []

        for mpim in mpims:
            mpim_members = {"name": mpim["name"], "users": [] if "members" not in mpim.keys() else [self.__USER_DATA.setdefault(m, deleted_user(m)) for m in mpim["members"]]}
            all_mpim_users.append(mpim_members)

        return all_mpim_users

    @staticmethod
    def _extract_time(json):
        try:
            # Convert the timestamp part to float
            return float(json['ts'])
        except KeyError:
            return 0

    def slack_name(self):
        """Returns the (guessed) slack name"""
        return self._slack_name

    def archive_path(self):
        """Returns the archive path"""
        return self._PATH

    def warn_not_found_to_hide_channels(self):
        """Print error if not all channels to hide have been found"""
        if self._remaining_unhidden_channels:
            logging.warning(f"Error: Could not find all channels to hide: {self._remaining_unhidden_channels}")

    ###################
    # Private Methods #
    ###################

    def _create_messages(self, names, data, isDms=False):
        """
        Creates object of arrays of messages from each json file specified by the names or ids

        :param [str] names: names of each group of messages

        :param [object] data: array of objects detailing where to get the messages from in
        the directory structure

        :param bool isDms: boolean value used to tell if the data is dm data so the function can
        collect the empty dm directories and store them in memory only

        :return: object of arrays of messages

        :rtype: object
        """

        chats = {}
        empty_dms = []
        formatter = SlackFormatter(self.__USER_DATA, data)

        # Channel name to channel id mapping. Needed to create a messages
        # permalink with at least slackdump exports
        channel_name_to_id = {}
        for c in data.values():
            if "name" in c:
                channel_name_to_id[c["name"]] = c["id"]
            else:
                # direct messages have no channel name and are also
                # stored with the the id's folder.
                channel_name_to_id[c["id"]] = c["id"]

        for name in names:
            # gets path to dm directory that holds the json archive
            dir_path = os.path.join(self._PATH, name)
            messages = []
            # array of all days archived
            day_files = glob.glob(os.path.join(dir_path, "*.json"))

            # this is where it's skipping the empty directories
            if not day_files:
                if isDms:
                    empty_dms.append(name)
                continue

            for day in sorted(day_files):
                with io.open(os.path.join(self._PATH, day), encoding="utf8") as f:
                    # loads all messages
                    day_messages = json.load(f)

                    # sorts the messages in the json file
                    day_messages.sort(key=Reader._extract_time)

                    c_id = channel_name_to_id[name]
                    for d in day_messages:
                        msg_obj = Message(formatter, d, c_id, self._slack_name)
                        if self._filter_user(msg_obj):
                            messages.append(msg_obj)

            chats[name] = messages
        chats = self._build_threads(chats)

        if isDms:
            self._EMPTY_DMS = empty_dms

        return chats

    def _filter_user(self, msg_obj):
        if not self.filter_user_attribute:
            return True

        user = msg_obj.user
        if not user:
            return False

        attr = self.filter_user_attribute
        val = self.filter_user_value

        if attr == "id":
            return user["id"] == val
        elif attr == "name":
            return user["name"] == val
        elif attr == "real_name":
            return user._raw.get("real_name") == val
        elif attr == "email":
            return user.email == val
        elif attr == "display_name":
            return user.display_name == val
        else:
            return False

    def _build_threads(self, channel_data):
        """
        Re-orders the JSON to allow for thread building.
        Threads are identified by thread_ts and grouped under their parent message.

        :param [dict] channel_data: dictionary of all Slack channels and messages
        :return: None
        """
        for channel_name in channel_data.keys():
            messages = channel_data[channel_name]

            if not messages:
                continue

            replies = {}
            ts_to_index = {}  # Map of ts -> message index for O(1) parent lookup
            items_to_remove = set()

            # First pass: build ts_to_index map and identify thread replies
            for i, msg in enumerate(messages):
                ts = msg._message.get('ts')
                thread_ts = msg._message.get('thread_ts')

                # Track all messages by their ts for parent lookup
                if ts:
                    ts_to_index[ts] = i

                # If message has a thread_ts that differs from its own ts, it's a reply
                if ts and thread_ts and thread_ts != ts:
                    parent_index = ts_to_index.get(thread_ts)

                    if parent_index is not None:
                        if parent_index not in replies:
                            replies[parent_index] = []
                        replies[parent_index].append((i, msg))

            # Second pass: process main messages and their replies
            for location, message in enumerate(messages):
                # Remove channel join/leave messages if configured
                if self._config.skip_channel_member_change and message._message.get('subtype') in ['channel_join', 'channel_leave']:
                    items_to_remove.add(location)
                    # Any replies to the removed message stay top-level
                    replies.pop(location, None)
                    continue

                # If this message has replies, process them
                if location in replies:
                    reply_list = replies[location]

                    # Sort replies by their timestamp
                    sorted_replies = sorted(reply_list, key=lambda tup: float(tup[1]._message['ts']))

                    # Mark replies for removal from top-level and add thread note
                    for reply_index, reply_msg in sorted_replies:
                        items_to_remove.add(reply_index)

                        msgtext = reply_msg._message.get("text", "")
                        if self._config.thread_note and not reply_msg.is_thread_msg:
                            reply_msg._message["text"] = f"**Thread Reply:** {msgtext}"
                        reply_msg.is_thread_msg = True

                    # Store sorted replies under this parent
                    replies[location] = [msg for _, msg in sorted_replies]

            # Remove marked messages from top-level (in reverse order to preserve indices)
            for idx in sorted(items_to_remove, reverse=True):
                messages[idx] = {'user': -1}

            # Insert replies back into channel_data at correct positions
            sorted_threads = OrderedDict(sorted(replies.items(), reverse=True))
            for parent_location, thread_replies in sorted_threads.items():
                insert_location = parent_location + 1
                for reply in thread_replies:
                    messages.insert(insert_location, reply)
                    insert_location += 1

            # Filter out placeholder objects created during removal
            channel_data[channel_name] = [
                item for item in messages
                if isinstance(item, Message)
            ]

        # Apply timeframe filtering if configured
        if self._since:
            channel_data = self._message_filter_timeframe(channel_data.copy())

        return channel_data

    def _read_from_json(self, file):
        """
        Reads the file specified from json and creates an object based on the id of each element

        :param str file: Path to file of json to read

        :return: object of data read from json file

        :rtype: object
        """

        try:
            with io.open(os.path.join(self._PATH, file), encoding="utf8") as f:
                return {u["id"]: u for u in json.load(f)}
        except IOError:
            return {}

    def _message_filter_timeframe(self, channel_data):
        """
        It might be more efficient to filter the messages in the thread sorting
        loop. Yet, this is a more straightforward approach, especially factoring
        in the thread/non-thread message ids etc.

        Messages & threads need to be provided in a sorted form
        """
        for channel in channel_data.keys():
            messages_in_thread = []
            last_thread_message_in_timeframe = False
            delete_messages = []

            for location, message in enumerate(channel_data[channel]):
                is_msg_in_timeframe = self._message_in_timeframe(message)

                # Update message object for representation differences
                # at rendering
                if not is_msg_in_timeframe:
                    message.is_recent_msg = False

                # new main message
                if not message.is_thread_msg:
                    if not last_thread_message_in_timeframe:
                        delete_messages.extend(messages_in_thread)
                    messages_in_thread = [location]
                # Thread message
                else:
                    messages_in_thread.append(location)

                last_thread_message_in_timeframe = is_msg_in_timeframe

            # Last thread/message...
            if not last_thread_message_in_timeframe:
                delete_messages.extend(messages_in_thread)

            # Remove all messages that are not in the timeframe
            for loc in sorted(delete_messages, reverse=True):
                del channel_data[channel][loc]

        # remove channels without recent message
        for channel in list(channel_data.keys()):
            if not channel_data[channel]:
                del channel_data[channel]

        return channel_data

    def _message_in_timeframe(self, msg):
        """
        Returns true if message timestamp is older as since
        """
        if not self._since:
            return True

        ts = msg._message.get('ts')
        ts_obj = datetime.datetime.fromtimestamp(float(ts))

        return self._since < ts_obj

    def _get_slack_name(self):
        """
        Returns the slack name that should be https://<slackname>.slack.com

        Since slackdump doesn't contain the name, the function assumed that the
        name of the zip file or directory is the slack name. This is a weak
        assumption.

        It's name ise used for the permalink generation.
        """
        return pathlib.Path(self._PATH).stem

    def _remove_hidden_channels(self, channel_names):
        """Remove hidden channels from the list of channel names"""
        if self._remaining_unhidden_channels:
            # copy to make code shorter
            unhidden = self._remaining_unhidden_channels

            to_remove = set(unhidden).intersection(channel_names)
            unhidden = [c for c in unhidden if c not in to_remove]
            channel_names = [c for c in channel_names if c not in to_remove]

            self._remaining_unhidden_channels = unhidden

        return channel_names
