import hashlib
import json
import os
import zipfile
import glob

from slackviewer.message import Message


def get_channel_list(path):
    channels = [ c["name"] for c in get_channels(path).values() ]
    return channels


def compile_channels(path, user_data, channel_data):
    channels = get_channel_list(path)
    chats = {}
    for channel in channels:
        channel_dir_path = os.path.join(path, channel)
        messages = []
        day_files = glob.glob(os.path.join(channel_dir_path, "*.json"))
        if not day_files:
            continue
        for day in sorted(day_files, reverse=False):
            with open(os.path.join(path, day)) as f:
                day_messages = json.load(f)
                messages.extend([Message(user_data, channel_data, d) for d in
                                 day_messages])
        chats[channel] = messages
    return chats


def get_users(path):
    with open(os.path.join(path, "users.json")) as f:
        return {u["id"]: u for u in json.load(f)}


def get_channels(path):
    with open(os.path.join(path, "channels.json")) as f:
        return {u["id"]: u for u in json.load(f)}


def SHA1_file(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


def extract_archive(filepath):
    if os.path.isdir(filepath):
        print("Archive already extracted. Viewing from %s") %(filepath)
        return(os.path.abspath(filepath))

    if not zipfile.is_zipfile(filepath):
        # Misuse of TypeError? :P
        raise TypeError("{} is not a zipfile".format(filepath))

    archive_sha = SHA1_file(filepath)
    extracted_path = os.path.join("/tmp", "_slackviewer", archive_sha)
    if os.path.exists(extracted_path):
        print("{} already exists".format(extracted_path))
    else:
        # Extract zip
        with zipfile.ZipFile(filepath) as zip:
            print("{} extracting to {}...".format(
                filepath,
                extracted_path))
            zip.extractall(path=extracted_path)
        print("{} extracted to {}.".format(filepath, extracted_path))
        # Add additional file with archive info
        archive_info = {
            "sha1": archive_sha,
            "filename": os.path.split(filepath)[1]
        }
        with open(
            os.path.join(
                extracted_path,
                ".slackviewer_archive_info.json"
            ), 'w+'
        ) as f:
            json.dump(archive_info, f)

    return extracted_path
