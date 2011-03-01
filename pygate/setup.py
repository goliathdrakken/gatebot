#!/usr/bin/env python

from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages

VERSION = "0.1.0"
SHORT_DESCRIPTION = "Gatebot gate controller software"
LONG_DESCRIPTION = """This package contains Gatebot gate controller and Django
frontend package.

**Note:** This package is still *experimental* and subject to change.
"""

setup(
    name = "gatebot",
    version = VERSION,
    description = SHORT_DESCRIPTION,
    long_description = LONG_DESCRIPTION,
    author = "jared szechy",
    author_email = "jared.szechy@gmail.com",
    url = "http://goliathonline.com/",
    packages = find_packages('src'),
    package_dir = {
      '' : 'src',
    },
    scripts = [
      'distribute_setup.py',
      'src/pygate/bin/gateboard_daemon.py',
      'src/pygate/bin/gateboard_monitor.py',
      'src/pygate/bin/gate-admin.py',
      'src/pygate/bin/gate_core.py',
      'src/pygate/bin/gate_master.py',
      'src/pygate/bin/gatenetproxy.py',
      'src/pygate/bin/lcd_daemon.py',
    ],
    install_requires = [
      'django >= 1.2',
      'django-autoslug',
      'django-imagekit >= 0.3.3',
      'django-registration',
      'django_extensions',

      #'MySQL-python',
      'pylcdui >= 0.5.5',
      'python-gflags >= 1.3',
      'South >= 0.7.3',
      'Sphinx',
      'django_nose',
      'tweepy',
      'pytz',
    ],
    include_package_data = True,

)
