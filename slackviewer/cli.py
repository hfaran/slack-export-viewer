import click
import pkgutil
import shutil
import os.path

from datetime import datetime

from jinja2 import Environment, PackageLoader
from slackviewer.config import Config
from slackviewer.constants import SLACKVIEWER_TEMP_PATH
from slackviewer.reader import Reader
from slackviewer.utils.click import envvar, flag_ennvar


@click.group()
def cli():
    pass


@cli.command(help="Cleans up any temporary files (including cached output by slack-export-viewer)")
@click.option("--wet", "-w", is_flag=True,
              default=flag_ennvar("SEV_CLEAN_WET"),
              help="Actually performs file deletion")
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
@click.option('--debug', is_flag=True, default=flag_ennvar("FLASK_DEBUG"))
@click.option('--show-dms', is_flag=True, default=False, help="Show direct messages")
@click.option("--since", default=None, type=click.DateTime(formats=["%Y-%m-%d"]),
              help="Only show messages since this date.")
@click.option('--skip-channel-member-change', is_flag=True, default=False, envvar='SKIP_CHANNEL_MEMBER_CHANGE', help="Hide channel join/leave messages")
@click.option("--template", default=None, type=click.File('r'), help="Custom single file export template")
@click.option("--hide-channels", default=None, type=str, help="Comma separated list of channels to hide.", envvar="HIDE_CHANNELS")
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
