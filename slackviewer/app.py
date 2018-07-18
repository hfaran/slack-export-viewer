import os
import flask
from flask import request, redirect, url_for, flash
from slackviewer.archive import extract_archive
from slackviewer.reader import Reader


app = flask.Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

app.config["UPLOAD_FOLDER"] = "archives"
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2 GB limit

reader = Reader()

# these functions only fire when the route is navigated to

@app.route("/channel/<name>/")
def channel_name(name):
    if not hasattr(reader, 'channels'):
        return flask.render_template("404.html")
    messages = reader.channels[name]
    channels = list(reader.channels.keys())
    groups = list(reader.groups.keys())
    dm_users = list(reader.dm_users)
    mpim_users = list(reader.mpim_users)

    return flask.render_template("viewer.html", messages=messages,
                                 name=name.format(name=name),
                                 channels=sorted(channels),
                                 groups=sorted(groups),
                                 dm_users=dm_users,
                                 mpim_users=mpim_users)


@app.route("/group/<name>/")
def group_name(name):
    if not hasattr(reader, 'channels'):
        return flask.render_template("404.html")
    messages = reader.groups[name]
    channels = list(reader.channels.keys())
    groups = list(reader.groups.keys())
    dm_users = list(reader.dm_users)
    mpim_users = list(reader.mpim_users)

    return flask.render_template("viewer.html", messages=messages,
                                 name=name.format(name=name),
                                 channels=sorted(channels),
                                 groups=sorted(groups),
                                 dm_users=dm_users,
                                 mpim_users=mpim_users)


@app.route("/dm/<id>/")
def dm_id(id):
    if not hasattr(reader, 'channels'):
        return flask.render_template("404.html")
    messages = reader.dms[id]
    channels = list(reader.channels.keys())
    groups = list(reader.groups.keys())
    dm_users = list(reader.dm_users)
    mpim_users = list(reader.mpim_users)

    return flask.render_template("viewer.html", messages=messages,
                                 id=id.format(id=id),
                                 channels=sorted(channels),
                                 groups=sorted(groups),
                                 dm_users=dm_users,
                                 mpim_users=mpim_users)


@app.route("/mpim/<name>/")
def mpim_name(name):
    if reader.channels is None:
        return flask.render_template("404.html")
    messages = reader.mpims[name]
    channels = list(reader.channels.keys())
    groups = list(reader.groups.keys())
    dm_users = list(reader.dm_users)
    mpim_users = list(reader.mpim_users)

    return flask.render_template("viewer.html", messages=messages,
                                 name=name.format(name=name),
                                 channels=sorted(channels),
                                 groups=sorted(groups),
                                 dm_users=dm_users,
                                 mpim_users=mpim_users)


ALLOWED_EXTENSIONS = set(["zip"])

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def upload():
    print('upload')
    if request.method == "POST":
        # check if the post request has the file part
        print(request.files)
        if "archive_file" not in request.files:
            print('archive_file not in request.file')
            flash("No file part")
            return redirect(request.url)
        file = request.files["archive_file"]
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == "":
            print("file name is empty")
            flash("No selected file")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            print(os.path.abspath(file.filename))
            filename = os.path.abspath(file.filename) # change this to full file path for where it gets uploaded to
            archive_path = extract_archive(filename)
            reader.set_path(archive_path)
            reader.get_all_messages()
            return redirect(url_for("index"))

    reader.reset()
    return flask.render_template("upload.html", reader=reader)


@app.route("/channel/")
def index():
    if not hasattr(reader, 'channels'):
        return flask.render_template("404.html")
    channels = list(reader.channels.keys())
    if "general" in channels:
        return channel_name("general")
    else:
        return channel_name(channels[0])
