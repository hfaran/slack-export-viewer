import hashlib
import io
from os import path

import pytest

import slackviewer
from slackviewer import archive
from slackviewer.utils.six import to_bytes


def test_SHA1_file():
    filepath = path.join("tests", "testarchive.zip")
    version = to_bytes(slackviewer.__version__)

    def SHA1_file(filepath, extra=b''):
        """The original unoptimized method (reads whole file instead of chunks)"""
        with io.open(filepath, 'rb') as f:
            return hashlib.sha1(f.read() + extra).hexdigest()

    expected = SHA1_file(filepath, version)
    actual = archive.SHA1_file(filepath, version)
    assert actual == expected
