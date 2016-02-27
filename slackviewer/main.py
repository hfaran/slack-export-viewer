import os

import click
import flask

from slackviewer.app import app
from slackviewer.archive import \
    extract_archive, \
    get_users, \
    get_channels, \
    compile_channels


def envvar(name, default):
    """Create callable environment variable getter

    :param str name: Name of environment variable
    :param default: Default value to return in case it isn't defined
    """
    return lambda: os.environ.get(name, default)


def debug_ennvar():
    return os.environ.get('FLASK_DEBUG') == '1'


@click.command()
@click.option('-p', '--port', default=envvar('SEV_PORT', '5000'),
              type=click.INT, help="Host port to serve your content on")
@click.option("-z", "--archive", type=click.Path(), required=True,
              default=envvar('SEV_ARCHIVE', ''),
              help="Path to your Slack export archive (.zip file)")
@click.option('-I', '--ip', default=envvar('SEV_IP', '0.0.0.0'),
              type=click.STRING, help="Host IP to serve your content on")
@click.option('--debug', is_flag=True, default=debug_ennvar())
def main(port, archive, ip, debug):
    if not archive:
        raise ValueError("Empty path provided for archive")

    app.debug = debug
    if app.debug:
        print("WARNING: DEBUG MODE IS ENABLED!")
    app.config["PROPAGATE_EXCEPTIONS"] = True

    path = extract_archive(archive)
    user_data = get_users(path)
    channel_data = get_channels(path)
    channels = compile_channels(path, user_data, channel_data)

    top = flask._app_ctx_stack
    top.channels = channels

    app.run(
        host=ip,
        port=port
    )
