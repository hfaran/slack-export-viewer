import click
import pkgutil
import shutil
import os.path

from datetime import datetime

from jinja2 import Environment, PackageLoader
from slackviewer.config import Config
from slackviewer.constants import SLACKVIEWER_TEMP_PATH
from slackviewer.reader import Reader


@click.group()
def cli():
    pass


@cli.command(help="Cleans up any temporary files (including cached output by slack-export-viewer)")
@click.option("--wet", "-w", is_flag=True, default=False, envvar='SEV_CLEAN_WET', help="""\b
    Actually performs file deletion
    Environment var: SEV_CLEAN_WET (default: false)
    """)
def clean(wet):
    if wet:
        if os.path.exists(SLACKVIEWER_TEMP_PATH):
            print("Removing {}...".format(SLACKVIEWER_TEMP_PATH))
            shutil.rmtree(SLACKVIEWER_TEMP_PATH)
        else:
            print("Nothing to remove! {} does not exist.".format(SLACKVIEWER_TEMP_PATH))
    else:
        print("Run with -w to remove {}".format(SLACKVIEWER_TEMP_PATH))


@cli.command(help="Generates a single-file printable export for an archive file or directory")
@click.option('--debug', is_flag=True, default=False, envvar='SEV_DEBUG', help="""\b
    Enable debug mode
    Environment var: SEV_DEBUG (default: false)
    """)
@click.option('--show-dms/--no-show-dms', default=False, envvar='SEV_SHOW_DMS', help="""\b
    Show/Hide direct messages"
    Environment var: SEV_SHOW_DMS (default: false)
    """)
@click.option('--thread-note/--no-thread-note', default=True, envvar='SEV_THREAD_NOTE', help="""\b
    Add/don't add 'Thread Reply' to thread messages.
    Environment var: SEV_THREAD_NOTE (default: true)
    """)
@click.option("--since", default=None, type=click.DateTime(formats=["%Y-%m-%d"]), envvar='SEV_SINCE', help="""\b
    Only show messages since the given date
    Environment var: SEV_SINCE (default: None)
    """)
@click.option('--skip-channel-member-change', is_flag=True, default=False, envvar='SEV_SKIP_CHANNEL_MEMBER_CHANGE', help="""\b
    Hide channel join/leave messages
    Environment var: SEV_SKIP_CHANNEL_MEMBER_CHANGE (default: false)
    """)
@click.option("--template", default=None, type=click.File('r'), envvar='SEV_TEMPLATE', help="""\b
    Custom single file export template
    Environment var: SEV_TEMPLATE (default: "export_single.html")
    """)
@click.option("--hide-channels", default=None, type=str, envvar="SEV_HIDE_CHANNELS", help="""\b
    Comma separated list of channels to hide.
    Environment var: SEV_HIDE_CHANNELS (default: None)
    """)
@click.argument('archive')
def export(**kwargs):
    config = Config(kwargs)

    css = pkgutil.get_data('slackviewer', 'static/viewer.css').decode('utf-8')

    tmpl = Environment(loader=PackageLoader('slackviewer')).get_template("export_single.html")
    if config.template:
        tmpl = Environment(loader=PackageLoader('slackviewer')).from_string(config.template.read())
    r = Reader(config)
    channel_list = sorted(
        [{"channel_name": k, "messages": v} for (k, v) in r.compile_channels().items()],
        key=lambda d: d["channel_name"]
    )

    dm_list = []
    mpims = []
    if config.show_dms:
        #
        # Direct DMs
        dm_list = r.compile_dm_messages()
        dm_users = r.compile_dm_users()

        # make list better lookupable. Also hide own user in 1:1 DMs
        dm_users = {dm['id']: dm['users'][0].display_name for dm in dm_users}

        # replace id with slack username
        dm_list = [{'name': dm_users[k], 'messages': v} for k, v in dm_list.items()]

        #
        # Group DMs
        mpims = r.compile_mpim_messages()
        mpim_users = r.compile_mpim_users()

        # make list better lookupable
        mpim_users = {g['name']: g['users'] for g in mpim_users}
        # Get the username instead of object
        mpim_users = {k: [u.display_name for u in v] for k, v in mpim_users.items()}
        # make the name a string
        mpim_users = {k: ', '.join(v) for k, v in mpim_users.items()}

        # replace id with group member list
        mpims = [{'name': mpim_users[k], 'messages': v} for k, v in mpims.items()]

    r.warn_not_found_to_hide_channels()

    html = tmpl.render(
        css=css,
        generated_on=datetime.now(),
        workspace_name=r.slack_name(),
        source_file=os.path.basename(config.archive),
        channels=channel_list,
        dms=dm_list,
        mpims=mpims,
    )
    filename = f"{r.slack_name()}.html"
    with open(filename, 'wb') as outfile:
        outfile.write(html.encode('utf-8'))

    print(f"Exported to {filename}")
