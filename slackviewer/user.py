# User info wrapper object
import logging

class User(object):
    """
    Wrapper object around an entry in users.json. Behaves like a read-only dictionary if
    asked, but adds some useful logic to decouple the front end from the JSON structure.
    """

    _NAME_KEYS = ["display_name", "real_name"]
    _DEFAULT_IMAGE_KEY = "image_512"

    def __init__(self, raw_data):
        self._raw = raw_data

    def __getitem__(self, key):
        return self._raw[key]

    @property
    def display_name(self):
        """
        Find the most appropriate display name for a user: look for a "display_name", then
        a "real_name", and finally fall back to the always-present "name".
        """
        for k in self._NAME_KEYS:
            if self._raw.get(k):
                return self._raw[k]
            if "profile" in self._raw and self._raw["profile"].get(k):
                return self._raw["profile"][k]
        return self._raw["name"]

    @property
    def email(self):
        """
        Shortcut property for finding the e-mail address or bot URL.
        """
        if "profile" in self._raw:
            email = self._raw["profile"].get("email")
        elif "bot_url" in self._raw:
            email = self._raw["bot_url"]
        else:
            email = None
        if not email:
            logging.debug("No email found for %s", self._raw.get("name"))
        return email

    def image_url(self, pixel_size=None):
        """
        Get the URL for the user icon in the desired pixel size, if it exists. If no
        size is supplied, give the URL for the full-size image.
        """
        if "profile" not in self._raw:
            return
        profile = self._raw["profile"]
        if (pixel_size):
            img_key = "image_%s" % pixel_size
            if img_key in profile:
                return profile[img_key]
        return profile[self._DEFAULT_IMAGE_KEY]


def deleted_user(id):
    """
    Create a User object for a deleted user.
    """
    deleted_user = {
        "id": id,
        "name": "deleted-" + id,
        "deleted": True,
        "is_bot": False,
        "is_app_user": False,
    }
    return User(deleted_user)
