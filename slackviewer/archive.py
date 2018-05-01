import hashlib
import json
import os
import zipfile
import io

import slackviewer
from slackviewer.constants import SLACKVIEWER_TEMP_PATH
from slackviewer.utils.six import to_unicode, to_bytes

def SHA1_file(filepath, extra=""):
    """
    Returns hex digest of SHA1 hash of file at filepath

    :param str filepath: File to hash

    :param bytes extra: Extra content added to raw read of file before taking hash

    :return: hex digest of hash

    :rtype: str
    """

    with io.open(filepath, 'rb') as f:
        return hashlib.sha1(f.read() + extra).hexdigest()


def extract_archive(filepath):
    """
    Returns the path of the archive

    :param str filepath: Path to file to extract or read

    :return: path of the archive

    :rtype: str
    """

    # Checks if file path is a directory
    if os.path.isdir(filepath):
        path = os.path.abspath(filepath)
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
            print("{} extracting to {}...".format(filepath, extracted_path))
            zip.extractall(path=extracted_path)

        print("{} extracted to {}".format(filepath, extracted_path))

        # Add additional file with archive info
        create_archive_info(filepath, extracted_path, archive_sha)

    return extracted_path


# Saves archive info
# When loading empty dms and there is no info file then this is called to
# create a new archive file
def create_archive_info(filepath, extracted_path, archive_sha=None):
    """
    Saves archive info to a json file

    :param str filepath: Path to directory of archive

    :param str extracted_path: Path to directory of archive

    :param str archive_sha: SHA string created when archive was extracted from zip
    """

    archive_info = {
        "sha1": archive_sha,
        "filename": os.path.split(filepath)[1],
    }

    with io.open(
        os.path.join(
            extracted_path,
            ".slackviewer_archive_info.json",
        ), 'w+', encoding="utf-8"
    ) as f:
        s = json.dumps(archive_info, ensure_ascii=False)
        s = to_unicode(s)
        f.write(s)
