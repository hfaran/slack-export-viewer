from collections import OrderedDict

import glob
import io
import json
import os

from slackviewer.formatter import SlackFormatter
from slackviewer.message import Message
from slackviewer.user import User


class Reader(object):
    """
    Reader object will read all of the archives' data from the json files
    """

    def __init__(self, PATH):
        self._PATH = PATH
        # TODO: Make sure this works
        with io.open(os.path.join(self._PATH, "users.json"), encoding="utf8") as f:
            self.__USER_DATA = {u["id"]: User(u) for u in json.load(f)}

    ##################
    # Public Methods #
    ##################

    def compile_channels(self, channels=None):
        if isinstance(channels, str):
            channels = channels.split(',')

        channel_data = self._read_from_json("channels.json")
        channel_names = [c["name"] for c in channel_data.values() if not channels or c["name"] in channels]

        return self._create_messages(channel_names, channel_data)

    def compile_groups(self):

        group_data = self._read_from_json("groups.json")
        group_names = [c["name"] for c in group_data.values()]

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
                    dm_members = {"id": dm["id"], "users": [self.__USER_DATA[m] for m in dm["members"]]}
                    all_dms_users.append(dm_members)
                except KeyError:
                    dm_members = None

        return all_dms_users

    def compile_mpim_messages(self):

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
            mpim_members = {"name": mpim["name"], "users": [self.__USER_DATA[m] for m in mpim["members"]]}
            all_mpim_users.append(mpim_members)

        return all_mpim_users

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
                 
                    messages.extend([Message(formatter, d) for d in day_messages])

            chats[name] = messages
        chats = self._build_threads(chats)

        if isDms:
            self._EMPTY_DMS = empty_dms

        return chats

    def _build_threads(self, channel_data):
        """
        Re-orders the JSON to allow for thread building.

        :param [dict] channel_data: dictionary of all Slack channels and messages

        :return: None
        """
        for channel_name in channel_data.keys():
            if channel_name in channel_data:
                replies = {}
                for message in channel_data[channel_name]:
                    #   If there's a "reply_count" key, generate a list of user and timestamp dictionaries
                    if 'reply_count' in message._message.keys():
                        #   Identify and save where we are
                        location = channel_data[channel_name].index(message)
                        reply_list = []
                        for reply in message._message['replies']:
                            reply_list.append(reply)
                        reply_objects = []
                        for item in reply_list:
                            for answer in channel_data[channel_name]:
                                if "user" in answer._message:
                                    if answer._message['user'] == item['user'] \
                                            and answer._message['ts'] == item['ts']:
                                        reply_location = channel_data[channel_name].index(answer)
                                        # Mutate the original dictionary. We're going to put the thread replies after
                                        # the original message.
                                        thread_message = channel_data[channel_name].pop(reply_location)
                                        reply_objects.append(thread_message)
                        replies[location] = reply_objects
                # Create an OrderedDict of thread locations and replies in reverse numerical order
                sorted_threads = OrderedDict(sorted(replies.items(), reverse=True))

                # Iterate through the threads and insert them back into channel_data[channel_name] in response order
                for grouping in sorted_threads.items():
                    location = grouping[0] + 1
                    for reply in grouping[1]:
                        if not reply._message["text"].startswith("**Thread Reply:**"):
                            reply._message["text"] = "**Thread Reply:** {}".format(reply._message['text'])
                        channel_data[channel_name].insert(location, reply)
                        location += 1
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
