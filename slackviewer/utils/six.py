"""Poor man's version Six"""

import sys


PY_VERSION = sys.version_info[0]


def to_unicode(s):
    """Convert str s to unicode

    :param str s: string
    :return: "unicode" version of s (unicode in py2, str in py3)
    """
    if PY_VERSION == 2:
        s = unicode(s)

    return s


def to_bytes(s, encoding="utf8"):
    """Converts str s to bytes"""
    if PY_VERSION == 2:
        b = bytes(s)
    elif PY_VERSION == 3:
        b = bytes(s, encoding)
    else:
        raise ValueError("Is Python 4 out already?")

    return b
