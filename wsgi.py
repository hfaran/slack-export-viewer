"""
It exposes the WSGI callable as a module-level variable named ``application``.

Just makes the app availible as application for gunicorn

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

from slackviewer.app import app as application
