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

"""Wrapper module for database implementation."""

import datetime
import logging
import socket

from django.db.utils import DatabaseError

from pygate.core import kb_common
from pygate.core import config
from pygate.core import models
from pygate.core import protolib

from pygate.web.api import krest

class BackendError(Exception):
  """Base backend error exception."""

class NoTokenError(BackendError):
  """Token given is unknown."""

class Backend:
  """Abstract base Gatebot backend class.

  This class defines the interface that pygate uses to talk to the gatebot
  backend.
  """

  def GetConfig(self):
    """Returns a GatebotConfig instance based on the current database values."""
    raise NotImplementedError

  def CreateNewUser(self, username, gender=kb_common.DEFAULT_NEW_USER_GENDER,
      weight=kb_common.DEFAULT_NEW_USER_WEIGHT):
    """Creates a new User instance.

    Args
      username: the unique username for the new User
      gender: the gender to assign the new user
      weight: the weight to assign the new user
    Returns
      the new User instance
    """
    raise NotImplementedError

  def GetAllGates(self):
    """Returns all currently enabled gates."""
    raise NotImplementedError

  def RecordEntry(self, tap_name, username=None, pour_time=None,
      duration=0, auth_token=None):
    """Records a new drink with the given parameters."""
    raise NotImplementedError

  def GetAuthToken(self, auth_device, token_value):
    """Returns an AuthenticationToken instance."""
    raise NotImplementedError


class GatebotBackend(Backend):
  """Django models backed Backend."""

  def __init__(self, sitename='default', site=None):
    self._logger = logging.getLogger('backend')
    self._config = config.GatebotConfig(self._GetConfigDict())
    if site:
      self._site = site
    else:
      self._site = models.GatebotSite.objects.get(name=sitename)

  def _GetConfigDict(self):
    try:
      ret = {}
      for row in models.Config.objects.all():
        ret[row.key] = row.value
      return ret
    except DatabaseError, e:
      raise BackendError, e

  def _GetGateFromName(self, gate_name):
    try:
      return models.Gate.objects.get(site=self._site, name=gate_name)
    except models.Gate.DoesNotExist:
      return None

  def _GetUserObjFromUsername(self, username):
    try:
      return models.User.objects.get(username=username)
    except models.User.DoesNotExist:
      return None

  def GetConfig(self):
    return self._config

  def CreateNewUser(self, username, gender=kb_common.DEFAULT_NEW_USER_GENDER,
      weight=kb_common.DEFAULT_NEW_USER_WEIGHT):
    u = models.User(username=username)
    u.save()
    p = u.get_profile()
    p.gender = gender
    p.weight = weight
    p.save()
    return protolib.ToProto(u)

  def CreateAuthToken(self, auth_device, token_value, username=None):
    token = models.AuthenticationToken.objects.create(
        site=self._site, auth_device=auth_device, token_value=token_value)
    if username:
      user = self._GetUserObjFromUsername(username)
      token.user = user
    token.save()
    return protolib.ToProto(token)

  def GetAllGates(self):
    return protolib.ToProto(list(models.Gate.objects.all()))

  def RecordDrink(self, tap_name, username=None, pour_time=None,
      duration=0, auth_token=None):

    gate = self._GetGateFromName(gate_name)
    if not gate:
      raise BackendError, "Gate unknown"

    user = None
    if username:
      user = self._GetUserObjFromUsername(username)

    if not pour_time:
      pour_time = datetime.datetime.now()

    d = models.Entry(site=self._site, user=user,
        starttime=pour_time, duration=duration,
        auth_token=auth_token)
    d.save()
    d.PostProcess()

    return protolib.ToProto(d)


  def GetAuthToken(self, auth_device, token_value):

    # Special case for "core.user" psuedo auth device.
    if auth_device == 'core.user':
      try:
        user = models.User.objects.get(username=token_value, is_active=True)
      except models.User.DoesNotExist:
        raise NoTokenError(auth_device)
      fake_token = models.AuthenticationToken(auth_device='core.user',
          token_value=token_value, seqn=0, user=user, enabled=True)
      return protolib.ToProto(fake_token)

    tok, created = models.AuthenticationToken.objects.get_or_create( site=self._site,
        auth_device=auth_device, token_value=token_value)
    if not tok.user:
      raise NoTokenError
    return protolib.ToProto(tok)


class WebBackend(Backend):
  def __init__(self, api_url=None, api_key=None):
    self._logger = logging.getLogger('api-backend')
    self._client = krest.KrestClient(api_url=api_url, api_key=api_key)

  def GetConfig(self):
    raise NotImplementedError

  def CreateNewUser(self, username, gender=kb_common.DEFAULT_NEW_USER_GENDER,
      weight=kb_common.DEFAULT_NEW_USER_WEIGHT):
    raise NotImplementedError

  def CreateAuthToken(self, auth_device, token_value, username=None):
    raise NotImplementedError

  def GetAllGates(self):
    ts = self._client.GateStatus()
    return (d['gate'] for d in self._client.GateStatus()['gates'])

  def RecordEntry(self, tap_name, username=None, pour_time=None,
      duration=0, auth_token=None):
    return self._client.RecordEntry(gate_name=gate_name, username=username,
        pour_time=pour_time, duration=duration, auth_token=auth_token)

  def GetAuthToken(self, auth_device, token_value):
    try:
      response = self._client.GetToken(auth_device, token_value)
      token = response['token']
      return token
    except krest.NotFoundError:
      raise NoTokenError
    except socket.error:
      self._logger.warning('Socket error fetching token; ignoring.')
      raise NoTokenError
