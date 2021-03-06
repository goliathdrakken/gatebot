#!/usr/bin/env python
#
# Copyright 2009 Mike Wakerly <opensource@hoho.com>
#
# This file is part of the Pygate package of the Gatebot project.
# For more information on Pygate or Gatebot, see http://gatebot.org/
#
# Pygate is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Pygate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pygate.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

_DEBUG = False

SYSTEM_SETTINGS_DIR = "/etc/gatebot"
HOME_DIR = os.environ.get('HOME')
USER_SETTINGS_DIR = os.path.join(HOME_DIR, '.gatebot')

# Greatest precedence: $HOME/.gatebot/
# Next precedence: /etc/gatebot
SEARCH_DIRS = (
    USER_SETTINGS_DIR,
    SYSTEM_SETTINGS_DIR,
)

def _Debug(message):
  if _DEBUG:
    sys.stderr.write('importhacks: %s\n' % (message,))

def _Warning(message):
  sys.stderr.write('importhacks: %s\n' % (message,))

def _AddToSysPath(paths):
  for path in paths:
    path = os.path.abspath(path)
    if path not in sys.path:
      _Debug('Adding to sys.path: %s' % path)
      sys.path.append(path)
    else:
      _Debug('Already in sys.path: %s' % path)

def _ExtendSysPath():
  """ Add some paths where we'll look for user settings. """
  paths = []
  for dir in SEARCH_DIRS:
    paths.append(dir)
    if _DEBUG:
      test_settings = os.path.join(dir, 'common_settings.py')
      if os.path.exists(test_settings):
        _Debug('%s exists' % test_settings)
      else:
        _Debug('%s does NOT exist' % test_settings)

  _AddToSysPath(paths)

def _SetDjangoSettingsEnv(settings='pygate.settings'):
  """ Set django settings if not set. """
  if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    _Debug('Setting DJANGO_SETTINGS_MODULE=%s' % (settings,))
    os.environ['DJANGO_SETTINGS_MODULE'] = settings

def _FixAll():
  try:
    import pygate
    pygate_dir = os.path.dirname(pygate.__file__)
    _Debug('Pygate loaded from dir: %s' % pygate_dir)
  except ImportError:
    _Warning('Error: pygate could not be imported')
    sys.exit(1)

  _ExtendSysPath()
  _SetDjangoSettingsEnv()

  try:
    import common_settings
    common_dir = os.path.dirname(common_settings.__file__)
    _Debug('common_settings loaded from dir: %s' % common_dir)
  except ImportError:
    _Warning('Warning: common_settings could not be imported')

if __name__ == '__main__' or os.environ.get('DEBUG_IMPORT_HACKS'):
  # When run as a program, or DEBUG_IMPORT_HACKS is set: print debug info
  _DEBUG = True

_FixAll()
