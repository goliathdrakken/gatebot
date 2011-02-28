# Copyright 2010 Mike Wakerly <opensource@hoho.com>
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

"""Routines from converting data to and from Protocol Buffer format."""

import sys
import time

from pygate.core import models
from pygate.core.util import AttrDict

_CONVERSION_MAP = {}

def converts(kind):
  def decorate(f):
    global _CONVERSION_MAP
    _CONVERSION_MAP[kind] = f
    return f
  return decorate

def ToProto(obj, full=False):
  """Converts the object to protocol format."""
  if obj is None:
    return None
  kind = obj.__class__
  if hasattr(obj, '__iter__'):
    return (ToProto(item, full) for item in obj)
  elif kind in _CONVERSION_MAP:
    return _CONVERSION_MAP[kind](obj, full)
  else:
    raise ValueError, "Unknown object type: %s" % kind

### Model conversions

@converts(models.AuthenticationToken)
def AuthTokenToProto(record, full=False):
  ret = AttrDict()
  ret.id = record.seqn
  ret.auth_device = record.auth_device
  ret.token_value = record.token_value
  if record.user:
    ret.username = str(record.user.username)
  else:
    ret.username = None
  ret.nice_name = record.nice_name
  if full:
    ret.enabled = record.enabled
    ret.created_time = record.created
    if record.expires:
      ret.expire_time = record.expires
    if record.pin:
      ret.pin = record.pin
  return ret

@converts(models.Gate)
def GateToProto(tap, full=False):
  ret = AttrDict()
  ret.id = str(tap.seqn)
  ret.name = tap.name
  if tap.description:
    ret.description = tap.description
  return ret

@converts(models.User)
def UserToProto(user, full=False):
  ret = AttrDict()
  ret.username = user.username
  ret.mugshot_url = user.get_profile().MugshotUrl()
  ret.is_active = user.is_active
  if full:
    ret.first_name = user.first_name
    ret.last_name = user.last_name
    ret.email = user.email
    ret.password = user.password
    ret.is_staff = user.is_staff
    ret.is_active = user.is_active
    ret.is_superuser = user.is_superuser
    ret.last_login = user.last_login
    ret.date_joined = user.date_joined
  return ret

@converts(models.UserProfile)
def UserProfileToProto(record, full=False):
  ret = AttrDict()
  ret.username = record.user.username
  ret.gender = record.gender
  ret.weight = record.weight
  return ret

@converts(models.SystemEvent)
def SystemEventToProto(record, full=False):
  ret = AttrDict()
  ret.id = record.seqn
  ret.kind = record.kind
  ret.time = record.when
  if record.drink:
    ret.drink = record.drink.seqn
  if record.keg:
    ret.keg = record.keg.seqn
  if record.session:
    ret.session = record.session.seqn
  if record.user:
    ret.user = record.user.username
  return ret
