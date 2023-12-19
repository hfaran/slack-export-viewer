import click
import pkgutil
import shutil
import os.path

from datetime import datetime

from slackviewer.constants import SLACKVIEWER_TEMP_PATH
from slackviewer.utils.click import envvar, flag_ennvar
from slackviewer.reader import Reader
from slackviewer.archive import get_export_info
from jinja2 import Environment, PackageLoader


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
@click.argument('archive_dir')
def export(archive_dir):
    css = pkgutil.get_data('slackviewer', 'static/viewer.css').decode('utf-8')
    tmpl = Environment(loader=PackageLoader('slackviewer')).get_template("export_single.html")
    export_file_info = get_export_info(archive_dir)
    r = Reader(export_file_info["readable_path"])
    channel_list = sorted(
        [{"channel_name": k, "messages": v} for (k, v) in r.compile_channels().items()],
        key=lambda d: d["channel_name"]
    )

    html = tmpl.render(
        css=css,
        generated_on=datetime.now(),
        workspace_name=export_file_info["workspace_name"],
        source_file=export_file_info["basename"],
        channels=channel_list
    )
    with open(export_file_info['stripped_name'] + '.html', 'w') as outfile:
        outfile.write(html.encode('utf-8'))
