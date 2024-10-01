import os

import flask


app = flask.Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

app.data = app.app_ctx_globals_class()

@app.route("/channel/<name>/")
def channel_name(name):
    messages = app.data.channels[name]
    channels = list(app.data.channels.keys())
    groups = list(app.data.groups.keys()) if app.data.groups else {}
    dm_users = list(app.data.dm_users)
    mpim_users = list(app.data.mpim_users)

    return flask.render_template("viewer.html", messages=messages,
                                 name=name.format(name=name),
                                 channels=sorted(channels),
                                 groups=sorted(groups) if groups else {},
                                 dm_users=dm_users,
                                 mpim_users=mpim_users,
                                 no_sidebar=app.no_sidebar,
                                 no_external_references=app.no_external_references)


def send_file(name, attachment):
    try_path = os.path.join(app.data.path, name, "attachments", attachment)
    if os.path.exists(try_path):
        return flask.send_file(try_path)
    try_path = os.path.join(app.data.path, "__uploads", attachment)
    return flask.send_file(try_path)
    

@app.route("/channel/<name>/attachments/<attachment>")
def channel_name_attachment(name, attachment):
    return send_file(name, attachment)


@app.route("/channel/<name>/__uploads/<path>/<attachment>")
def channel_name_path_attachment(name, path, attachment):
    return send_file(name, os.path.join(path, attachment))


@app.route("/group/<name>/")
def group_name(name):
    messages = app.data.groups[name]
    channels = list(app.data.channels.keys())
    groups = list(app.data.groups.keys())
    dm_users = list(app.data.dm_users)
    mpim_users = list(app.data.mpim_users)

    return flask.render_template("viewer.html", messages=messages,
                                 name=name.format(name=name),
                                 channels=sorted(channels),
                                 groups=sorted(groups),
                                 dm_users=dm_users,
                                 mpim_users=mpim_users,
                                 no_sidebar=app.no_sidebar,
                                 no_external_references=app.no_external_references)


@app.route("/group/<name>/attachments/<attachment>")
def group_name_attachment(name, attachment):
    return send_file(name, attachment)


@app.route("/group/<name>/__uploads/<path>/<attachment>")
def group_name_path_attachment(name, path, attachment):
    return send_file(name, os.path.join(path, attachment))


@app.route("/dm/<id>/")
def dm_id(id):
    messages = app.data.dms[id]
    channels = list(app.data.channels.keys())
    groups = list(app.data.groups.keys())
    dm_users = list(app.data.dm_users)
    mpim_users = list(app.data.mpim_users)

    return flask.render_template("viewer.html", messages=messages,
                                 id=id.format(id=id),
                                 channels=sorted(channels),
                                 groups=sorted(groups),
                                 dm_users=dm_users,
                                 mpim_users=mpim_users,
                                 no_sidebar=app.no_sidebar,
                                 no_external_references=app.no_external_references)


@app.route("/dm/<name>/attachments/<attachment>")
def dm_name_attachment(name, attachment):
    return send_file(name, attachment)


@app.route("/dm/<name>/__uploads/<path>/<attachment>")
def dm_name_path_attachment(name, path, attachment):
    return send_file(name, os.path.join(path, attachment))


@app.route("/mpim/<name>/")
def mpim_name(name):
    messages = app.data.mpims.get(name, list())
    channels = list(app.data.channels.keys())
    groups = list(app.data.groups.keys())
    dm_users = list(app.data.dm_users)
    mpim_users = list(app.data.mpim_users)

    return flask.render_template("viewer.html", messages=messages,
                                 name=name.format(name=name),
                                 channels=sorted(channels),
                                 groups=sorted(groups),
                                 dm_users=dm_users,
                                 mpim_users=mpim_users,
                                 no_sidebar=app.no_sidebar,
                                 no_external_references=app.no_external_references)


@app.route("/mpim/<name>/attachments/<attachment>")
def mpim_name_attachment(name, attachment):
    return send_file(name, attachment)


@app.route("/mpim/<name>/__uploads/<path>/<attachment>")
def mpim_name_path_attachment(name, path, attachment):
    return send_file(name, os.path.join(path, attachment))


@app.route("/")
def index():
    channels = list(app.data.channels.keys())
    groups = list(app.data.groups.keys())
    dms = list(app.data.dms.keys())
    mpims = list(app.data.mpims.keys())
    if channels:
        if "general" in channels:
            return flask.redirect(flask.url_for(channel_name.__name__, name="general"))
        else:
            return flask.redirect(flask.url_for(channel_name.__name__, name=channels[0]))
    elif groups:
        return flask.redirect(flask.url_for(group_name.__name__, name=groups[0]))
    elif dms:
        return flask.redirect(flask.url_for(dm_id.__name__, id=dms[0]))
    elif mpims:
        return flask.redirect(flask.url_for(mpim_name.__name__, name=mpims[0]))
    else:
        return "No content was found in your export that we could render."
