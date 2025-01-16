import webbrowser
import os

import click
import flask

from slackviewer.app import app
from slackviewer.archive import extract_archive
from slackviewer.reader import Reader
from slackviewer.freezer import CustomFreezer
from slackviewer.utils.click import envvar, flag_ennvar


def configure_app(app, archive, channels, config):
    app.debug = config.get("debug", False)
    app.no_sidebar = config.get("no_sidebar", False)
    app.no_external_references = config.get("no_external_references", False)
    if app.debug:
        print("WARNING: DEBUG MODE IS ENABLED!")
    app.config["PROPAGATE_EXCEPTIONS"] = True

    path = extract_archive(archive)
    reader = Reader(path, config)

    top = flask._app_ctx_stack
    top.path = path
    top.channels = reader.compile_channels(channels)
    top.groups = reader.compile_groups()
    top.dms = {}
    top.dm_users = []
    top.mpims = {}
    top.mpim_users = []
    if not config.get("skip_dms", False):
        top.dms = reader.compile_dm_messages()
        top.dm_users = reader.compile_dm_users()
        top.mpims = reader.compile_mpim_messages()
        top.mpim_users = reader.compile_mpim_users()


    # remove any empty channels & groups. DM's are needed for now
    # since the application loads the first
    top.channels = {k: v for k, v in top.channels.items() if v}
    top.groups = {k: v for k, v in top.groups.items() if v}


@click.command()
@click.option('-p', '--port', default=envvar('SEV_PORT', '5000'),
              type=click.INT, help="Host port to serve your content on")
@click.option("-z", "--archive", type=click.Path(exists=True), required=True,
              envvar='SEV_ARCHIVE',
              help="Path to your Slack export archive (.zip file or directory)")
@click.option('-I', '--ip', default=envvar('SEV_IP', 'localhost'),
              type=click.STRING, help="Host IP to serve your content on")
@click.option('--no-browser', is_flag=True,
              default=flag_ennvar("SEV_NO_BROWSER"),
              help="If you do not want a browser to open "
                   "automatically, set this.")
@click.option('--channels', type=click.STRING,
              default=envvar("SEV_CHANNELS", None),
              help="A comma separated list of channels to parse.")
@click.option('--no-sidebar', is_flag=True,
              default=flag_ennvar("SEV_NO_SIDEBAR"),
              help="Removes the sidebar.")
@click.option('--no-external-references', is_flag=True,
              default=flag_ennvar("SEV_NO_EXTERNAL_REFERENCES"),
              help="Removes all references to external css/js/images.")
@click.option('--test', is_flag=True, default=flag_ennvar("SEV_TEST"),
              help="Runs in 'test' mode, i.e., this will do an archive extract, "
              "but will not start the server, and immediately quit.")
@click.option('--debug', is_flag=True, default=flag_ennvar("FLASK_DEBUG"))
@click.option("-o", "--output-dir", default="html_output", type=click.Path(),
              help="Output directory for static HTML files.")
@click.option("--html-only", is_flag=True, default=False,
              help="If you want static HTML only, set this.")
@click.option("--since", default=None, type=click.DateTime(formats=["%Y-%m-%d"]),
              help="Only show messages since this date.")
@click.option('--skip-dms', is_flag=True, default=False, help="Hide direct messages")
def main(
    port,
    archive,
    ip,
    no_browser,
    channels,
    no_sidebar,
    no_external_references,
    test,
    debug,
    output_dir,
    html_only,
    since,
    skip_dms,
):
    if not archive:
        raise ValueError("Empty path provided for archive")

    config = {
        "debug": debug,
        "since": since,
        "skip_dms": skip_dms,
        "no_sidebar": no_sidebar,
        "no_external_references": no_external_references,
    }
    configure_app(app, archive, channels, config)

    if html_only:
        # We need relative URLs, otherwise channel refs do not work
        app.config["FREEZER_RELATIVE_URLS"] = True

        # Custom subclass of Freezer allows overwriting the output directory
        freezer = CustomFreezer(app)
        freezer.cf_output_dir = output_dir

        # This tells freezer about the channel URLs
        @freezer.register_generator
        def channel_name():
            for channel in flask._app_ctx_stack.channels:
                yield {"name": channel}

        freezer.freeze()

        if not no_browser:
            webbrowser.open("file:///{}/index.html"
                            .format(os.path.abspath(output_dir)))

    elif not test:
        if not no_browser:
            webbrowser.open("http://{}:{}".format(ip, port))
        app.run(
            host=ip,
            port=port
        )
