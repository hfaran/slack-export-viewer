import click
import flask

from slackviewer.archive import \
    extract_archive, \
    get_users, \
    get_channels, \
    compile_channels


app = flask.Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)


@app.route("/channel/<name>")
def channel_name(name):
    messages = flask._app_ctx_stack.channels[name]
    channels = flask._app_ctx_stack.channels.keys()
    return flask.render_template("viewer.html", messages=messages,
                                 name=name.format(name=name),
                                 channels=sorted(channels))


@app.route("/")
def index():
    channels = flask._app_ctx_stack.channels.keys()
    if "general" in channels:
        return channel_name("general")
    else:
        return channel_name(channels[0])


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
