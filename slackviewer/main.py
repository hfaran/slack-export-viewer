import webbrowser

import click
import flask

from slackviewer.app import app
from slackviewer.archive import extract_archive
from slackviewer.reader import Reader
from slackviewer.utils.click import envvar, flag_ennvar


def configure_app(app, archive, debug):
    app.debug = debug
    if app.debug:
        print("WARNING: DEBUG MODE IS ENABLED!")
    app.config["PROPAGATE_EXCEPTIONS"] = True

    path = extract_archive(archive)
    reader = Reader(path)

    top = flask._app_ctx_stack
    top.channels = reader.compile_channels()
    top.groups = reader.compile_groups()
    top.dms = reader.compile_dm_messages()
    top.dm_users = reader.compile_dm_users()
    top.mpims = reader.compile_mpim_messages()
    top.mpim_users = reader.compile_mpim_users()


@click.command()
@click.option('-p', '--port', default=envvar('SEV_PORT', '5000'),
              type=click.INT, help="Host port to serve your content on")
@click.option("-z", "--archive", type=click.Path(), required=True,
              default=envvar('SEV_ARCHIVE', ''),
              help="Path to your Slack export archive (.zip file or directory)")
@click.option('-I', '--ip', default=envvar('SEV_IP', 'localhost'),
              type=click.STRING, help="Host IP to serve your content on")
@click.option('--no-browser', is_flag=True,
              default=flag_ennvar("SEV_NO_BROWSER"),
              help="If you do not want a browser to open "
                   "automatically, set this.")
@click.option('--test', is_flag=True, default=flag_ennvar("SEV_TEST"),
              help="Runs in 'test' mode, i.e., this will do an archive extract, but will not start the server,"
                   " and immediately quit.")
@click.option('--debug', is_flag=True, default=flag_ennvar("FLASK_DEBUG"))
def main(port, archive, ip, no_browser, test, debug):
    if not archive:
        raise ValueError("Empty path provided for archive")

    configure_app(app, archive, debug)

    if not no_browser and not test:
        webbrowser.open("http://{}:{}".format(ip, port))

    if not test:
        app.run(
            host=ip,
            port=port
        )
