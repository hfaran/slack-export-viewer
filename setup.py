import os
import codecs

from setuptools import setup, find_packages

import slackviewer


def read(filename):
    """Read and return `filename` in root dir of project and return string"""
    here = os.path.abspath(os.path.dirname(__file__))
    return codecs.open(os.path.join(here, filename), 'r', encoding='UTF-8').read()


install_requires = read("requirements.txt").split()
long_description = "See README at https://github.com/hfaran/slack-export-viewer"


setup(
    name="slack-export-viewer",
    version=slackviewer.__version__,
    url='https://github.com/hfaran/slack-export-viewer',
    license='MIT License',
    author='hfaran',
    author_email='private@private.com',
    description=('Slack Export Archive Viewer'),
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=install_requires,
    entry_points={'console_scripts': [
        'slack-export-viewer = slackviewer.main:main',
        'slack-export-viewer-cli = slackviewer.cli:cli'
    ]},
    include_package_data=True,
    # https://github.com/mitsuhiko/flask/issues/1562
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
)
