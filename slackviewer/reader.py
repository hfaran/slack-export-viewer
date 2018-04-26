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
    @property
    def compile_channels(self):

        channel_data = self._read_from_json("channels.json")
        channel_names = [c["name"] for c in channel_data.values()]

        return self._create_messages(channel_names, channel_data)

    @property
    def compile_groups(self):

        group_data = self._read_from_json("groups.json")
        group_names = [c["name"] for c in group_data.values()]

        return self._create_messages(group_names, group_data)

    # TODO Possibly need to check here for all dms
    @property
    def compile_dm_messages(self):
        # Gets list of dm objects with dm ID and array of members ids
        dm_data = self._read_from_json("dms.json")
        dm_ids = [c["id"] for c in dm_data.values()]

        return self._create_messages(dm_ids, dm_data)

    @property
    def compile_dm_users(self):
        """ Gets the info for the members within the dm """

        dm_data = self._read_from_json("dms.json")
        dms = [c for c in dm_data(self._PATH).values()]
        all_dms_users = []

        for dm in dms:
            # checks if messages actually exsist
            if dm["id"] not in empty_dms:
                dm_members = {"id": dm["id"], "users": [user_data[m] for m in dm["members"]]}
                all_dms_users.append(dm_members)

        return all_dms_users


    @property
    def compile_mpim_messages(self):

        mpim_data = self._read_from_json("mpims.json")
        mpim_names = [c["name"] for c in mpim_data.values()]

        return self._create_messages(mpim_names, mpim_data)

    ###################
    # Private Methods #
    ###################

    def _create_messages(self, names, data):

        chats = {}

        for name in names:

            # gets path to dm directory that holds the json archive
            dir_path = os.path.join(self._PATH, name)
            messages = []
            # array of all days archived
            day_files = glob.glob(os.path.join(dir_path, "*.json"))

            if not day_files:
                continue

            for day in sorted(day_files):
                with io.open(os.path.join(self._PATH, day)) as f:
                    # loads all messages
                    day_messages = json.load(f)
                    messages.extend([Message(self.__USER_DATA, data, d) for d in day_messages])

            chats[name] = messages

        return chats

    def _read_from_json(self, file):
        try:
            with io.open(os.path.join(self._PATH, file), encoding="utf8") as f:
                return {u["id"]: u for u in json.load(f)}
        except IOError:
            return {}



# is this returning the same objects? If so maybe not use this function
def get_dm_members_list(path):
    return


def get_mpim_members_list(path):
    return [c for c in get_mpims_from_json(self._PATH).values()]





def compile_mpim_users(path, user_data, dm_data):
    mpims = get_mpim_members_list(path)
    all_mpim_users = []
    for mpim in mpims:
        mpim_members = {"name": mpim["name"], "users": [user_data[m] for m in mpim["members"]]}
        all_mpim_users.append(mpim_members)

    return all_mpim_users








"""
def get_users_from_json(path):
    with io.open(os.path.join(self._PATH, "users.json"), encoding="utf8") as f:
        return {u["id"]: u for u in json.load(f)}





empty_dir_names = []


# finds and removes empty directories recursively
# Slack keeps track of every dm that has ever exsisted and creates directories
# for them however, there aren't always archives in those directories
# so we track them here to not display them in the list
def remove_empty_dirs(path):
    if not os.path.isdir(path):
        print ("null path or file")
        return

    # if non empty directory call remove_empty_dirs
    files = os.listdir(path)
    if len(files):
        for f in files:
            fullpath = os.path.join(path, f)
            if os.path.isdir(fullpath):
                remove_empty_dirs(fullpath)

    # if empty directory add to array and remove it
    files = os.listdir(path)
    if len(files) == 0:
        empty_dir_names.append(path[-9:])
        os.rmdir(path)

    return empty_dir_names


# I also need to check if the folders have already been deleted and create a
# list from that checking against empty conversations
def get_empty_dm_names_from_file(path):
    info = os.path.join(path, ".slackviewer_archive_info.json")
    if not os.path.exists(info):
        print ("creating new archive info file...")
        create_archive_info(path, path)

    with io.open(info) as i:
        empty_dms = json.load(i)["empty_dms"]
        if not len(empty_dms):
            return get_empty_dm_names_from_list(path)
        return empty_dms


# This is needed if the empty directories have already been removed
# it will check the list of dm ids against folders that exist
# on the top level of the directory
def get_empty_dm_names_from_list(path):
    empty_dir_names = []
    # list out files
    files = os.listdir(path)
    if len(files):
        for f in files:
            empty_dir_names.append(f)
            # if f in user_ids
            # empty_dir_names.append(f)

    return empty_dir_names


"""
