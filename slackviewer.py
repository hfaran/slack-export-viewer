#!/usr/bin/env python3

import os
import json
import datetime
import re

import click
import flask


app = flask.Flask(__name__)


class Message(object):
    def __init__(self, USER_DATA, message):
        self.__USER_DATA = USER_DATA
        self._message = message

    @property
    def type(self):
        return self._message["type"]

    @property
    def username(self):
        if "user" in self._message:
            return self.__USER_DATA[self._message["user"]]["name"]
        else:
            return self._message["username"]

    @property
    def user_id(self):
        return self._message["user"]

    @property
    def time(self):
        tsepoch = float(self._message["ts"].split(".")[0])
        return str(datetime.datetime.fromtimestamp(tsepoch)).split('.')[0]

    @property
    def msg(self):
        message = self._message["text"]
        # Handle "<@U0BM1CGQY|calvinchanubc> has joined the channel"
        message = re.sub(r"<@U0\w+\|[A-Za-z0-9.-_]+>",
                         self.annotated_mention, message)
        # Handle "<@U0BM1CGQY>"
        message = re.sub(r"<@U0\w+>", self.mention, message)
        return message

    @property
    def img(self):
        return self.__USER_DATA[self._message["user"]]["profile"]["image_72"]

    def mention(self, matchobj):
        return "@{}".format(
            self.__USER_DATA[matchobj.group(0)[2:-1]]["name"]
        )

    def annotated_mention(self, matchobj):
        return "@{}".format((matchobj.group(0)[2:-1]).split("|")[1])

def compile_channels(path, users):
    channels = [d for d in os.listdir(path)
                if os.path.isdir(os.path.join(path, d))]
    chats = {}
    for channel in channels:
        channel_dir_path = os.path.join(path, channel)
        messages = []
        for day in os.listdir(channel_dir_path):
            with open(os.path.join(channel_dir_path, day)) as f:
                day_messages = json.load(f)

                # messages.extend([Message(users, d) for d in day_messages])

                ms = []
                for d in day_messages:
                    try:
                        m = Message(users, d)
                    except:
                        print(d)
                        raise
                    ms.append(m)
                messages.extend(ms)

        chats[channel] = messages
    return chats


def get_users(path):
    with open(os.path.join(path, "users.json")) as f:
        return {u["id"]: u for u in json.load(f)}


@app.route("/elections")
def elections():
    messages = flask._app_ctx_stack.channels["elections"]
    return flask.render_template("archive.html", messages=messages)


@click.command()
@click.option("-d", "--dir", required=True)
@click.option("-p", "--port", default=5000, type=click.INT)
def main(dir, port):
    users = get_users(dir)
    channels = compile_channels(dir, users=users)

    top = flask._app_ctx_stack
    top.channels = channels

    app.debug = True
    app.run(
        host='0.0.0.0',
        port=port
    )


if __name__ == '__main__':
    main()
