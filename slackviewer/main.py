import click
import flask

from slackviewer.app import app
from slackviewer.archive import \
    extract_archive, \
    get_users, \
    get_channels, \
    compile_channels


@click.command()
@click.option("-p", "--port", default=5000, type=click.INT)
@click.option("-z", "--archive", type=click.Path(), required=True)
def main(port, archive):
    path = extract_archive(archive)
    user_data = get_users(path)
    channel_data = get_channels(path)
    channels = compile_channels(path, user_data, channel_data)

    top = flask._app_ctx_stack
    top.channels = channels

    app.debug = True
    app.run(
        host='0.0.0.0',
        port=port
    )
