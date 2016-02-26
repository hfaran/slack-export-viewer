#!/usr/bin/env python3

import os
import json
import datetime
import re

import click
import flask
import markdown2


app = flask.Flask(__name__)


class Message(object):
    def __init__(self, USER_DATA, CHANNEL_DATA, message):
        self.__USER_DATA = USER_DATA
        self.__CHANNEL_DATA = CHANNEL_DATA
        self._message = message

    ##############
    # Properties #
    ##############

    @property
    def user_id(self):
        return self._message["user"]

    @property
    def username(self):
        try:
            return self.__USER_DATA[self._message["user"]]["name"]
        except KeyError:
            # In case this is a bot or something, we fallback to "username"
            if"username" in self._message:
                return self._message["username"]
            # If that fails to, it's probably USLACKBOT...
            else:
                return self._message["user"]

    @property
    def time(self):
        # Handle this: "ts": "1456427378.000002"
        tsepoch = float(self._message["ts"].split(".")[0])
        return str(datetime.datetime.fromtimestamp(tsepoch)).split('.')[0]

    @property
    def msg(self):
        message = self._message["text"]
        # Handle "<@U0BM1CGQY|calvinchanubc> has joined the channel"
        message = re.sub(r"<@U0\w+\|[A-Za-z0-9.-_]+>",
                         self._annotated_mention, message)
        # Handle "<@U0BM1CGQY>"
        message = re.sub(r"<@U0\w+>", self._mention, message)
        # Handle "<http(s|)://...>"
        message = re.sub(r"<http(s|)://.*>", self._url, message)
        # Handle hashtags (that are meant to be hashtags and not headings)
        message = re.sub(r"^#\S+", self._hashtag, message)
        # Handle channel references
        message = re.sub(r"<#C0\w+>", self._channel_ref, message)

        message = markdown2.markdown(message, extras=["cuddled-lists"]).strip()
        # markdown2 likes to wrap everything in <p> tags
        if message.startswith("<p>") and message.endswith("</p>"):
            message = message[3:-4]

        return message

    @property
    def img(self):
        try:
            return self.__USER_DATA[self._message["user"]]["profile"]["image_72"]
        except KeyError:
            return ""

    ###################
    # Private Methods #
    ###################

    def _mention(self, matchobj):
        return "@{}".format(
            self.__USER_DATA[matchobj.group(0)[2:-1]]["name"]
        )

    def _annotated_mention(self, matchobj):
        return "@{}".format((matchobj.group(0)[2:-1]).split("|")[1])

    def _url(self, matchobj):
        compound = matchobj.group(0)[1:-1]
        if len(compound.split("|")) == 2:
            url, title = compound.split("|")
        else:
            url, title = compound, compound
        return "[{title}]({url})".format(url=url, title=title)

    def _hashtag(self, matchobj):
        text = matchobj.group(0)
        return "_{}_".format(text)

    def _channel_ref(self, matchobj):
        channel_id = matchobj.group(0)[2:-1]
        channel_name = self.__CHANNEL_DATA[channel_id]["name"]
        return "_#{}_".format(channel_name)


def compile_channels(path, user_data, channel_data):
    channels = [d for d in os.listdir(path)
                if os.path.isdir(os.path.join(path, d))]
    chats = {}
    for channel in channels:
        channel_dir_path = os.path.join(path, channel)
        messages = []
        for day in os.listdir(channel_dir_path):
            with open(os.path.join(channel_dir_path, day)) as f:
                day_messages = json.load(f)
                messages.extend([Message(user_data, channel_data, d) for d in
                                 day_messages])
        chats[channel] = messages
    return chats


def get_users(path):
    with open(os.path.join(path, "users.json")) as f:
        return {u["id"]: u for u in json.load(f)}


def get_channels(path):
    with open(os.path.join(path, "channels.json")) as f:
        return {u["id"]: u for u in json.load(f)}


@app.route("/channel/<name>")
def channel_name(name):
    messages = flask._app_ctx_stack.channels[name]
    return flask.render_template("archive.html", messages=messages,
                                 title="#{name}".format(name=name))


@click.command()
@click.option("-d", "--dir", required=True)
@click.option("-p", "--port", default=5000, type=click.INT)
def main(dir, port):
    user_data = get_users(dir)
    channel_data = get_channels(dir)
    channels = compile_channels(dir, user_data, channel_data)

    top = flask._app_ctx_stack
    top.channels = channels

    app.debug = True
    app.run(
        host='0.0.0.0',
        port=port
    )


if __name__ == '__main__':
    main()
