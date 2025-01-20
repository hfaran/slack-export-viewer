import logging
import sys


class Config(object):
    """
    Config object to to retreive all config input and make sure all expected
    variables exist
    """
    def __init__(self, config):
        self._config = config

        # FYI: click verifies most types already as well as if files/dirs exist

        # Args used by both webserver and cli
        self.archive = config.get("archive")
        self.debug = config.get("debug")

        self.hide_channels = []
        if 'hide_channels' in config and config.get("hide_channels"):
            self.hide_channels = config['hide_channels'].split(',')

        self.since = config.get("since")
        self.skip_channel_member_change = config.get("skip_channel_member_change")

        # CLI only
        self.template = config.get("template")
        # Another branch exists already to unify them
        self.show_dms = config.get("show_dms")

        # webserver only setting
        self.ip = config.get("ip")
        self.port = config.get("port")
        self.no_browser = config.get("no_browser")
        self.channels = config.get("channels")
        self.no_sidebar = config.get("no_sidebar")
        self.no_external_references = config.get("no_external_references")
        self.test = config.get("test")
        self.debug = config.get("debug")
        self.output_dir = config.get("output_dir")
        self.html_only = config.get("html_only")
        # separate code exists to combine them. PR after this one
        self.skip_dms = config.get("skip_dms")

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
