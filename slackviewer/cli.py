import click
import shutil

from slackviewer.constants import SLACKVIEWER_TEMP_PATH
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
        print("Removing {}...".format(SLACKVIEWER_TEMP_PATH))
        shutil.rmtree(SLACKVIEWER_TEMP_PATH)
    else:
        print("Run with -w to remove {}".format(SLACKVIEWER_TEMP_PATH))
