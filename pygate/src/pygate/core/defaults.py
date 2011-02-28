# Copyright 2003-2009 Mike Wakerly <opensource@hoho.com>
#
# This file is part of the Pykeg package of the Kegbot project.
# For more information on Pykeg or Kegbot, see http://kegbot.org/
#
# Pykeg is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Pykeg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pykeg.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import math

from pygate.core import backend
from pygate.core import models
from pygate.core import units

def db_is_installed():
  try:
    models.Config.objects.get(key='db.installed')
    return True
  except models.Config.DoesNotExist:
    return False

def set_defaults():
  """ default values (contents may change with schema) """
  if db_is_installed():
    raise RuntimeError, "Database is already installed."

  site = models.KegbotSite.objects.create(name='default')

  # config table defaults
  default_config = (
     ('logging.logfile', 'gate.log'),
     ('logging.logformat', '%(asctime)s %(levelname)-8s (%(name)s) %(message)s'),
     ('logging.use_logfile', 'true'),
     ('logging.use_stream', 'true'),
     ('db.installed', 'true'),
  )
  for key, val in default_config:
    rec = models.Config(site=site, key=key, value=val)
    rec.save()

  # Gate defaults
  main_gate = models.Gate(site=site, name='Main Gate', description='The main gate')
  main_gate.save()

  b = backend.KegbotBackend()

def gentestdata():
  """ default values (contents may change with schema) """

  usernames = ['abe', 'bort', 'charlie']
  users = []
  b = backend.KegbotBackend()
  for name in usernames:
    users.append(b.CreateNewUser(name))
