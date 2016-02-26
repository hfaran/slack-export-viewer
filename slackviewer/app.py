import flask


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
