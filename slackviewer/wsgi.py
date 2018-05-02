"""
WSGI config for gettingstarted project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
from slackviewer.main import app

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "slackview.settings")
application = app

if __name__ == "__main__":
    application.run()
