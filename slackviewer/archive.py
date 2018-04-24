import hashlib
import json
import os
import zipfile
import glob
import io

import slackviewer
from slackviewer.constants import SLACKVIEWER_TEMP_PATH
from slackviewer.message import Message
from slackviewer.utils.six import to_unicode, to_bytes

# Create array of just the channel names
def get_channel_list(path):
    return [c["name"] for c in get_channels(path).values()]


def get_group_list(path):
    return [c["name"] for c in get_groups(path).values()]


# Gets the list of IDs from the array of dm objects
def get_dm_list(path):
    return [c["id"] for c in get_dms(path).values()]


# is this returning the same objects? If so maybe not use this function
def get_dm_members_list(path):
    return [c for c in get_dms(path).values()]


def get_mpim_list(path):
    return [c["name"] for c in get_mpims(path).values()]


def get_mpim_members_list(path):
    return [c for c in get_mpims(path).values()]


# Need to fix this if dir already exists then the path needs to be different somehow.
def compile_channels(path, user_data, channel_data):
    channels = get_channel_list(path)
    chats = {}
    for channel in channels:
        channel_dir_path = os.path.join(path, channel)
        messages = []
        day_files = glob.glob(os.path.join(channel_dir_path, "*.json"))
        if not day_files:
            continue
        for day in sorted(day_files):
            with io.open(os.path.join(path, day), encoding="utf8") as f:
                day_messages = json.load(f)
                messages.extend([Message(user_data, channel_data, d) for d in
                                 day_messages])
        chats[channel] = messages
    return chats


def compile_groups(path, user_data, group_data):
    groups = get_group_list(path)
    chats = {}
    for group in groups:
        group_dir_path = os.path.join(path, group)
        messages = []
        day_files = glob.glob(os.path.join(group_dir_path, "*.json"))
        if not day_files:
            continue
        for day in sorted(day_files):
            with io.open(os.path.join(path, day)) as f:
                day_messages = json.load(f)
                messages.extend([Message(user_data, group_data, d) for d in
                                 day_messages])
        chats[group] = messages
    return chats


def compile_dm_messages(path, user_data, dm_data):
    # Gets list of dm objects with dm ID and array of members ids
    dms = get_dm_list(path)
    chats = {}
    for dm in dms:
        # gets path to dm directory that holds the json archive
        dm_dir_path = os.path.join(path, dm)
        messages = []
        # array of all days archived
        day_files = glob.glob(os.path.join(dm_dir_path, "*.json"))
        if not day_files:
            continue
        for day in sorted(day_files):
            with io.open(os.path.join(path, day)) as f:
                # loads all messages
                day_messages = json.load(f)
                messages.extend([Message(user_data, dm_data, d) for d in
                                 day_messages])
        chats[dm] = messages
    return chats


# Gets the info for the members within the dm
def compile_dm_users(path, user_data, dm_data, empty_dms):
    dms = get_dm_members_list(path)
    all_dms_users = []
    for dm in dms:
        # checks if messages actually exsist
        if dm["id"] not in empty_dms:
            dm_members = {"id": dm["id"], "users": [user_data[m] for m in dm["members"]]}
            all_dms_users.append(dm_members)

    return all_dms_users


def compile_mpim_messages(path, user_data, mpim_data):
    mpims = get_mpim_list(path)
    chats = {}
    for mpim in mpims:
        mpim_dir_path = os.path.join(path, mpim)
        messages = []
        day_files = glob.glob(os.path.join(mpim_dir_path, "*.json"))
        if not day_files:
            continue
        for day in sorted(day_files):
            with io.open(os.path.join(path, day)) as f:
                day_messages = json.load(f)
                messages.extend([Message(user_data, mpim_data, d) for d in
                                 day_messages])
        chats[mpim] = messages
    return chats


def compile_mpim_users(path, user_data, dm_data):
    mpims = get_mpim_members_list(path)
    all_mpim_users = []
    for mpim in mpims:
        mpim_members = {"name": mpim["name"], "users": [user_data[m] for m in mpim["members"]]}
        all_mpim_users.append(mpim_members)

    return all_mpim_users


def get_users(path):
    with io.open(os.path.join(path, "users.json"), encoding="utf8") as f:
        return {u["id"]: u for u in json.load(f)}


def get_channels(path):
    with io.open(os.path.join(path, "channels.json"), encoding="utf8") as f:
        return {u["id"]: u for u in json.load(f)}


def get_groups(path):
    try:
        with io.open(os.path.join(path, "groups.json"), encoding="utf8") as f:
            return {u["id"]: u for u in json.load(f)}
    except IOError:
        return {}


# Gets the information for each dm converstation that has ever existed
# and then creates an array of objects assign the object to the id as the key
def get_dms(path):
    try:
        with io.open(os.path.join(path, "dms.json"), encoding="utf8") as f:
            return {u["id"]: u for u in json.load(f)}
    except IOError:
        return {}


def get_mpims(path):
    try:
        with io.open(os.path.join(path, "mpims.json"), encoding="utf8") as f:
            return {u["id"]: u for u in json.load(f)}
    except IOError:
        return {}


def SHA1_file(filepath, extra=""):
    """Returns hex digest of SHA1 hash of file at filepath

    :param str filepath: File to hash
    :param bytes extra: Extra content added to raw read of file before taking hash
    :return: hex digest of hash
    :rtype: str
    """
    with io.open(filepath, 'rb') as f:
        return hashlib.sha1(f.read() + extra).hexdigest()


def extract_archive(filepath):
    # Checks if file path is a directory
    if os.path.isdir(filepath):
        path = os.path.abspath(filepath)
        # Add additional file with archive info
        create_archive_info(path, path)
        print("Archive already extracted. Viewing from {}...".format(path))
        return path

    # Checks if the filepath is a zipfile and continues to extract if it is
    # if not it raises an error
    elif not zipfile.is_zipfile(filepath):
        # Misuse of TypeError? :P
        raise TypeError("{} is not a zipfile".format(filepath))

    archive_sha = SHA1_file(
        filepath=filepath,
        # Add version of slackviewer to hash as well so we can invalidate the cached copy
        #  if there are new features added
        extra=to_bytes(slackviewer.__version__)
    )

    extracted_path = os.path.join(SLACKVIEWER_TEMP_PATH, archive_sha)

    if os.path.exists(extracted_path):
        print("{} already exists".format(extracted_path))
    else:
        # Extract zip
        with zipfile.ZipFile(filepath) as zip:
            print("{} extracting to {}...".format(
                filepath,
                extracted_path))
            zip.extractall(path=extracted_path)
        print("{} extracted to {}".format(filepath, extracted_path))
        # Add additional file with archive info
        create_archive_info(filepath, extracted_path, archive_sha)

    return extracted_path


# Saves archive info
# When loading empty dms and there is no info file then this is called to
# create a new archive file
def create_archive_info(filepath, extracted_path, archive_sha=None):
    empty = remove_empty_dirs(extracted_path)
    archive_info = {
        "sha1": archive_sha,
        "filename": os.path.split(filepath)[1],
        "empty_dms": empty
    }
    print (empty)

    with io.open(
        os.path.join(
            extracted_path,
            ".slackviewer_archive_info.json",
        ), 'w+', encoding="utf-8"
    ) as f:
        s = json.dumps(archive_info, ensure_ascii=False)
        s = to_unicode(s)
        f.write(s)


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
def get_empty_dm_names(path):
    info = os.path.join(path, ".slackviewer_archive_info.json")
    if not os.path.exists(info):
        print ("creating new archive info file...")
        create_archive_info(path, path)

    with io.open(info) as i:
        return json.load(i)["empty_dms"]
