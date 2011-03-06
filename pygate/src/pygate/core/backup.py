# Copyright 2010 Mike Wakerly <opensource@hoho.com>
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

"""Dump/restore utility methods for Gatebot."""

import sys

from pygate.core import kbjson
from pygate.core import models
from pygate.core import protolib

from pygate.beerdb import models as bdb_models

def _no_log(msg):
  pass

def dump(output_fp, kbsite, indent=None, log_cb=_no_log):
  """Produce a dump of this Gatebot system to the given filestream.

  In its current format, the dump is plaintext JSON string consisting of all
  important data, including tap configuration, drink history, and user account
  details.

  All "derived" tables are NOT backed up.  These are tables with data that can
  be regenerated at any time without any loss of history.  Specifically:
    - session chunks
    - user session chunks
    - keg session chunks
    - keg stats
    - user stats
    - session stats
    - system events
  """
  res = {}
  items = (
      ('gates', kbsite.gates.all().order_by('id')),
      ('users', models.User.objects.all().order_by('id')),
      ('profiles', models.UserProfile.objects.all().order_by('id')),
      ('entries', kbsite.entries.valid().order_by('id')),
      ('tokens', kbsite.tokens.all().order_by('id')),
      ('configs', kbsite.configs.all()),
  )

  log_cb('Generating backup data ...')
  for name, qs in items:
    log_cb('  .. dumping %s' % name)
    res[name] = list(protolib.ToProto(qs, full=True))

  log_cb('Serializing and writing backup data ...')
  output_fp.write(kbjson.dumps(res, indent=indent))

def restore(input_fp, kbsite, log_cb=_no_log):
  def _log(obj):
    obj_cls = obj.__class__
    obj_name = obj_cls.__name__
    log_cb('  +++ %s: %s' % (obj_name, obj))

  data = kbjson.loads(input_fp.read())

  kbsite.gates.all().delete()
  for rec in data['gates']:
    gate = models.Gate(site=kbsite, seqn=int(rec.id))
    gate.name = rec.name
    gate.description = rec.get('description')
    gate.save()
    _log(gate)

  user_map = {}
  for rec in data.get('users', []):
    user = None

    # If there's already a user registered with this e-mail address, use it.
    if rec.email:
      user_qs = models.User.objects.filter(email=rec.email)
      if user_qs.count():
        user = user_qs[0]
        user_map[rec.username] = user
        _log(user)
        continue

    # Create a new user, creating a new unique username if necessary.
    iter = 0
    username = rec.username
    while True:
      username_qs = models.User.objects.filter(username=username)
      if not username_qs.count():
        break
      iter += 1
      username = '%s_%i' % (rec.username[:30], iter)

    user = models.User(username=username)
    user.first_name = rec.first_name
    user.last_name = rec.last_name
    user.email = rec.email
    user.password = rec.password
    user.is_active = rec.is_active
    user.last_login = rec.last_login
    user.date_joined = rec.date_joined

    # XXX non-prod
    user.is_staff = rec.is_staff
    user.is_superuser = rec.is_superuser

    user.save()
    user_map[rec.username] = user
    _log(user)

  for rec in data.get('profiles', []):
    user = user_map.get(rec.username)
    if not user:
      print 'Warning: profile for non-existant user: %s' % rec.username
      continue
    profile, created = models.UserProfile.objects.get_or_create(user=user)
    profile.gender = rec.gender
    profile.weight = rec.weight
    profile.save()
    _log(profile)

  kbsite.tokens.all().delete()
  for rec in data.get('tokens', []):
    token = models.AuthenticationToken(site=kbsite, seqn=int(rec.id))
    token.auth_device = rec.auth_device
    token.token_value = rec.token_value
    username = rec.get('username')
    if username:
      token.user = user_map[username]
    token.enabled = rec.enabled
    token.created = rec.created_time
    token.pin = rec.get('pin')
    token.save()
    _log(token)

  kbsite.entries.all().delete()
  for rec in data.get('entries', []):
    entry = models.Entry(site=kbsite, seqn=int(rec.id))
    entry.starttime = rec.pour_time
    entry.duration = rec.get('duration')
    entry.status = rec.status
    username = rec.get('user_id')
    if username:
      entry.user = user_map[username]
    entry.auth_token = rec.get('auth_token')
    entry.save()
    _log(entry)

  log_cb('Regenerating sessions ...')
  _RegenSessions(kbsite)
  log_cb('Regenerating stats ...')
  _RegenStats(kbsite)
  log_cb('Regenerating events ...')
  _RegenEvents(kbsite)

def _RegenSessions(kbsite):
  for d in kbsite.drinks.valid().order_by('starttime'):
    d.session.AddDrink(d)

def _RegenStats(kbsite):
  models.SystemStats.objects.filter(site=kbsite).delete()
  models.UserStats.objects.filter(site=kbsite).delete()
  models.KegStats.objects.filter(site=kbsite).delete()
  models.SessionStats.objects.filter(site=kbsite).delete()
  for d in kbsite.entries.valid().order_by('starttime'):
    d._UpdateSystemStats()
    d._UpdateUserStats()
    d._UpdateKegStats()
    d._UpdateSessionStats()

def _RegenEvents(kbsite):
  kbsite.events.all().delete()
  for d in kbsite.drinks.valid().order_by('starttime'):
    models.SystemEvent.ProcessEntry(d)
