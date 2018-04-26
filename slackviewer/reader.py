import json
import os
import glob
import io

from slackviewer.message import Message

class Reader(object):
    """
    Reader object will read all of the archives' data from the json files
    """

    def __init__(self, PATH):
        self._PATH = PATH
        # TODO: Make sure this works
        with io.open(os.path.join(self._PATH, "users.json"), encoding="utf8") as f:
            self.__USER_DATA = {u["id"]: u for u in json.load(f)}

    # Public Methods
    def compile_channels(self):

        channel_data = self._read_from_json("channels.json")
        channel_names = [c["name"] for c in channel_data.values()]

        return self._create_messages(channel_names, channel_data)

    def compile_groups(self):

        group_data = self._read_from_json("groups.json")
        group_names = [c["name"] for c in group_data.values()]

        return self._create_messages(group_names, group_data)

    # TODO Possibly need to check here for all dms
    def compile_dm_messages(self):
        # Gets list of dm objects with dm ID and array of members ids
        dm_data = self._read_from_json("dms.json")
        dm_ids = [c["id"] for c in dm_data.values()]

        return self._create_messages(dm_ids, dm_data, True)

    def compile_dm_users(self):
        """
        Gets the info for the members within the dm

        Returns a list of all dms with the members that have ever existed

        """

        dm_data = self._read_from_json("dms.json")
        print(dm_data)
        dms = [c for c in dm_data(self._PATH).values()]
        all_dms_users = []

        for dm in dms:
            # checks if messages actually exsist
            if dm["id"] not in self._EMPTY_DMS:
                dm_members = {"id": dm["id"], "users": [self.__USER_DATA[m] for m in dm["members"]]}
                all_dms_users.append(dm_members)

        return all_dms_users


    def compile_mpim_messages(self):

        mpim_data = self._read_from_json("mpims.json")
        mpim_names = [c["name"] for c in mpim_data.values()]

        return self._create_messages(mpim_names, mpim_data)

    def compile_mpim_users(self):

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

        chats = {}
        empty_dms = []

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
                with io.open(os.path.join(self._PATH, day)) as f:
                    # loads all messages
                    day_messages = json.load(f)
                    messages.extend([Message(self.__USER_DATA, data, d) for d in day_messages])

            chats[name] = messages

        if isDms:
            self._EMPTY_DMS = empty_dms

        return chats

    def _read_from_json(self, file):
        try:
            with io.open(os.path.join(self._PATH, file), encoding="utf8") as f:
                return {u["id"]: u for u in json.load(f)}
        except IOError:
            return {}
