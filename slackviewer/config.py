import logging
import sys


class Config(object):
    """
    Config object to to retreive all config input and make sure all expected
    variables exist
    """
    def __init__(self, config):
        """
        Create all supported configs.
        Click verifies most types already as well as if files/dirs exist
        """
        self._config = config

        # Args used by both webserver and cli
        self.archive = config.get("archive")
        self.debug = config.get("debug")

        self.hide_channels = []
        if 'hide_channels' in config and config.get("hide_channels"):
            self.hide_channels = config['hide_channels'].split(',')

        self.show_dms = config.get("show_dms")
        self.since = config.get("since")
        self.skip_channel_member_change = config.get("skip_channel_member_change")
        self.thread_note = config.get("thread_note")

        # CLI only
        self.template = config.get("template")
        # Another branch exists already to unify them

        # webserver only setting
        self.channels = config.get("channels")
        self.debug = config.get("debug")
        self.html_only = config.get("html_only")
        self.ip = config.get("ip")
        self.no_browser = config.get("no_browser")
        self.no_external_references = config.get("no_external_references")
        self.no_sidebar = config.get("no_sidebar")
        self.output_dir = config.get("output_dir")
        self.port = config.get("port")
        self.test = config.get("test")

        self.sanity_check()

    def sanity_check(self):
        """Make sure all variables exist"""
        for key in self._config:
            try:
                # check if self.<key> exists
                getattr(self, key)
            except AttributeError:
                logging.fatal(f"Configuration '{key}' is not implemented")
                sys.exit(1)
