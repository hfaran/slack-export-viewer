"""Extensions for use with click options"""

import os


def envvar(name, default):
    """Create callable environment variable getter

    :param str name: Name of environment variable
    :param default: Default value to return in case it isn't defined
    """
    return lambda: os.environ.get(name, default)


def flag_ennvar(name):
    return os.environ.get(name) == '1'
