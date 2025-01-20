# Slack Export Viewer

![CI](https://github.com/hfaran/slack-export-viewer/actions/workflows/ci.yml/badge.svg)
[![PyPI version](https://badge.fury.io/py/slack-export-viewer.svg)](http://badge.fury.io/py/slack-export-viewer)

A Slack Export archive viewer that allows you to easily view and share your 
Slack team's export (instead of having to dive into hundreds of JSON files).

![Preview](screenshot.png)


## Contents

* [Overview](#overview)
* [Installation](#installation)
* [Usage](#usage)
* [Acknowledgements](#acknowledgements)

## Overview

`slack-export-viewer` is useful for small teams on a free Slack plan (limited to 10,000 messages) who overrun their budget and ocassionally need a nice interface to refer back to previous messages. You get a web interface to easily scroll through all channels in the export without having to look at individual JSON files per channel per day.

`slack-export-viewer` can be used locally on one machine for yourself to explore an export, it can be run on a headless server (as it is a Flask web app) if you also want to serve the content to the rest of your team, or it can output HTML for deploying a static website.


## Installation

I recommend [`pipx`](https://github.com/pipxproject/pipx) for a nice
isolated install.

```bash
pipx install slack-export-viewer
```

Or just feel free to use `pip` as you like.

```bash
pip install slack-export-viewer
```

`slack-export-viewer` will be installed as an entry-point; run from anywhere.

```bash
$ slack-export-viewer --help
Usage: slack-export-viewer [OPTIONS]

Options:
  -p, --port INTEGER            Host port to serve your content on
  -z, --archive PATH            Path to your Slack export archive (.zip file
                                or directory)  [required]
  -I, --ip TEXT                 Host IP to serve your content on
  --no-browser                  If you do not want a browser to open
                                automatically, set this.
  --channels TEXT               A comma separated list of channels to parse.
  --no-sidebar                  Removes the sidebar.
  --no-external-references      Removes all references to external
                                css/js/images.
  --test                        Runs in 'test' mode, i.e., this will do an
                                archive extract, but will not start the
                                server, and immediately quit.
  --debug
  -o, --output-dir PATH         Output directory for static HTML files.
  --html-only                   If you want static HTML only, set this.
  --since [%Y-%m-%d]            Only show messages since this date.
  --skip-dms                    Hide direct messages
  --skip-channel-member-change  Hide channel join/leave messages
  --hide-channels TEXT          Comma separated list of channels to hide.
  --help                        Show this message and exit.
```


## Usage

### 1) Grab your Slack team's export

#### Option 1: official Slack export
* Visit [https://my.slack.com/services/export](https://my.slack.com/services/export)
* Create an export
* Wait for it to complete
* Refresh the page and download the export (.zip file) into whatever directory

#### Option 2: slackdump
* Download slackdump from https://github.com/rusq/slackdump/
* Setup authentication as outlined in the slackdump documentation
* Run slackdump and export messages in the "Standard" format as either a directory or zip file.
    * `slack-export-viewer` can also use the director without zip file.

### 2) Point `slack-export-viewer` to it

Point slack-export-viewer to the .zip file and let it do its magic

```bash
slack-export-viewer -z /path/to/export/zip
```

If everything went well, your archive will have been extracted and processed, and a browser window will have opened showing your *#general* channel from the export. Or, if the `html-only` flag was set, HTML files will be available in the `html-output` directory (or a different directory if specified).


## CLI

There is now a CLI included as well. Currently the one command you can use is clearing the cache from slack-export-viewer from your %TEMP% directory; see usage:

```bash
$ slack-export-viewer-cli --help
Usage: cli.py [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  clean   Cleans up any temporary files (including cached output by...
  export  Generates a single-file printable export for an archive file or...
```

Export:
```bash
$ slack-export-viewer-cli export --help
Usage: cli.py export [OPTIONS] ARCHIVE_DIR

  Generates a single-file printable export for an archive file or directory

Options:
  --debug
  --show-dms                    Show direct messages
  --since [%Y-%m-%d]            Only show messages since this date.
  --skip-channel-member-change  Hide channel join/leave messages
  --template FILENAME           Custom single file export template
  --hide-channels TEXT          Comma separated list of channels to hide.
  --help                        Show this message and exit.

```
An example template can be found in the repositories [`slackviewer/templates/example_template_single_export.html`](https://github.com/hfaran/slack-export-viewer/tree/master/slackviewer/templates/example_template_single_export.html) file

Clean
```bash
$ slack-export-viewer-cli clean --help
Usage: cli.py clean [OPTIONS]

  Cleans up any temporary files (including cached output by slack-export-
  viewer)

Options:
  -w, --wet  Actually performs file deletion
  --help     Show this message and exit.
```


### Examples

Clean:
```bash
$ slack-export-viewer-cli clean
Run with -w to remove C:\Users\hamza\AppData\Local\Temp\_slackviewer
$ slack-export-viewer-cli clean -w
Removing C:\Users\hamza\AppData\Local\Temp\_slackviewer...
```

Export:
```bash
$ slack-export-viewer-cli export \
    --since $(date -d "2 days ago" '+%Y-%m-%d') \
    --template /tmp/example_template_single_export.html \
    --show-dms \
    /tmp/slack-export
Archive already extracted. Viewing from /tmp/slack-export...
Exported to slack-export.html
```


## Local Development

After installing the requirements in requirements.txt and dev-requirements.txt, 
define `FLASK_APP` as `main` and select any channels desired from an export:

```bash
export FLASK_APP=main && export SEV_CHANNELS=general
```

Start a development server by running `app.py` in the root directory:

```bash
python3 app.py -z /Absolute/path/to/archive.zip --debug
```

## Acknowledgements

Credit to Pieter Levels whose [blog post](https://levels.io/slack-export-to-html/) and PHP script I used as a jumping off point for this.

### Improvements over Pieter's script

 `slack-export-viewer` is similar in core functionality but adds several things on top to make it nicer to use:

* An installable application
* Automated archive extraction and retention
* A Slack-like sidebar that lets you switch channels easily
* Much more "sophisticated" rendering of messages
* A Flask server which lets you serve the archive contents as opposed to a PHP script which does static file generation
