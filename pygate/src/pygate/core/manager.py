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

"""Tap (single path of fluid) management module."""

import datetime
import inspect
import time
import threading
import logging

from pygate.core import backend
from pygate.core import kb_common
from pygate.core import kbevent
from pygate.core import util


def EventHandler(event_type):
  def decorate(f):
    if not hasattr(f, 'events'):
      f.events = set()
    f.events.add(event_type)
    return f
  return decorate


class Manager:
  def __init__(self, name, event_hub):
    self._name = name
    self._event_hub = event_hub
    self._logger = logging.getLogger(self._name)

  def GetEventHandlers(self):
    ret = {}
    for name, method in inspect.getmembers(self, inspect.ismethod):
      if not hasattr(method, 'events'):
        continue
      for event_type in method.events:
        if event_type not in ret:
          ret[event_type] = set()
        ret[event_type].add(method)
    return ret

  def GetStatus(self):
    return []

  def _PublishEvent(self, event):
    """Convenience alias for EventHub.PublishEvent"""
    self._event_hub.PublishEvent(event)

class TokenRecord:
  STATUS_ACTIVE = 'active'
  STATUS_REMOVED = 'removed'

  def __init__(self, auth_device, token_value, tap_name):
    self.auth_device = auth_device
    self.token_value = token_value
    self.tap_name = tap_name
    self.last_seen = datetime.datetime.now()
    self.status = self.STATUS_ACTIVE

  def __str__(self):
    return '%s=%s@%s' % self.AsTuple()

  def AsTuple(self):
    return (self.auth_device, self.token_value, self.tap_name)

  def SetStatus(self, status):
    self.status = status

  def UpdateLastSeen(self):
    self.SetStatus(self.STATUS_ACTIVE)
    self.last_seen = datetime.datetime.now()

  def IdleTime(self):
    return datetime.datetime.now() - self.last_seen

  def IsPresent(self):
    return self.status == self.STATUS_ACTIVE

  def IsRemoved(self):
    return self.status == self.STATUS_REMOVED

  def __hash__(self):
    return hash((self.AsTuple(), other.AsTuple()))

  def __cmp__(self, other):
    if not other:
      return -1
    return cmp(self.AsTuple(), other.AsTuple())


class AuthenticationManager(Manager):
  def __init__(self, name, event_hub, backend):
    Manager.__init__(self, name, event_hub)
    self._backend = backend
    self._tokens = {}  # maps tap name to currently active token
    self._lock = threading.RLock()

  @EventHandler(kbevent.TokenAuthEvent)
  def HandleAuthTokenEvent(self, event):
    for tap in self._GetTapsForTapName(event.tap_name):
      record = self._GetRecord(event.auth_device_name, event.token_value,
          tap.GetName())
      if event.status == event.TokenState.ADDED:
        self._TokenAdded(record)
      else:
        self._TokenRemoved(record)

  def _GetRecord(self, auth_device, token_value, tap_name):
    new_rec = TokenRecord(auth_device, token_value, tap_name)
    existing = self._tokens.get(tap_name)
    if new_rec == existing:
      return existing
    return new_rec

  def _MaybeStartFlow(self, record):
    """Called when the given token has been added.

    This will either start or renew a flow on the FlowManager."""
    username = None
    tap_name = record.tap_name
    try:
      token = self._backend.GetAuthToken(record.auth_device, record.token_value)
      username = token.username
    except backend.NoTokenError:
      pass

    if not username:
      self._logger.info('Token not assigned: %s' % record)
      return

    max_idle = kb_common.AUTH_DEVICE_MAX_IDLE_SECS.get(record.auth_device)
    if max_idle is None:
      max_idle = kb_common.AUTH_DEVICE_MAX_IDLE_SECS['default']
    """self._flow_manager.StartFlow(tap_name, username=username,
        max_idle_secs=max_idle)"""

  def _MaybeEndFlow(self, record):
    """Called when the given token has been removed.

    If the auth device is a captive auth device, then this will forcibly end the
    flow.  Otherwise, this is a no-op."""
    is_captive = kb_common.AUTH_DEVICE_CAPTIVE.get(record.auth_device)
    if is_captive is None:
      is_captive = kb_common.AUTH_DEVICE_CAPTIVE['default']
    if is_captive:
      self._logger.debug('Captive auth device, ending flow immediately.')
      """self._flow_manager.StopFlow(record.tap_name)"""
    else:
      self._logger.debug('Non-captive auth device, not ending flow.')

  @util.synchronized
  def _TokenAdded(self, record):
    """Processes a record when a token is added."""
    self._logger.info('Token attached: %s' % record)
    existing = self._tokens.get(record.tap_name)

    if existing == record:
      # Token is already known; nothing to do except update it.
      record.UpdateLastSeen()
      return

    if existing:
      self._logger.info('Removing previous token')
      self._TokenRemoved(existing)

    self._tokens[record.tap_name] = record
    self._MaybeStartFlow(record)

  @util.synchronized
  def _TokenRemoved(self, record):
    self._logger.info('Token detached: %s' % record)
    if record != self._tokens.get(record.tap_name):
      self._logger.warning('Token has already been removed')
      return

    record.SetStatus(record.STATUS_REMOVED)
    del self._tokens[record.tap_name]
    self._MaybeEndFlow(record)

  def _GetTapsForTapName(self, tap_name):
    if tap_name == kb_common.ALIAS_ALL_TAPS:
      return self._tap_manager.GetAllTaps()
    else:
      if self._tap_manager.TapExists(tap_name):
        return [self._tap_manager.GetTap(tap_name)]
      else:
        return []


class SubscriptionManager(Manager):
  def __init__(self, name, event_hub, server):
    Manager.__init__(self, name, event_hub)
    self._server = server
  @EventHandler(kbevent.CreditAddedEvent)
  @EventHandler(kbevent.DrinkCreatedEvent)
  @EventHandler(kbevent.FlowUpdate)
  def RepostEvent(self, event):
    self._server.SendEventToClients(event)
