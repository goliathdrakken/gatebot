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

class Gate:
  def __init__(self, name):
    self._name = name

  def __str__(self):
    return self._name

  def GetName(self):
    return self._name


class GateManager(Manager):
  """Maintains listing of available fluid paths.

  This manager maintains the set of available beer taps.  Taps have a
  one-to-one correspondence with beer taps.  For example, a kegboard controller
  is capable of reading from two flow sensors; thus, it provides two beer
  taps.
  """

  def __init__(self, name, event_hub):
    Manager.__init__(self, name, event_hub)
    self._gates = {}

  def GetStatus(self):
    ret = []
    for gate in self.GetAllGates():
      meter = gate.GetMeter()
      ret.append('Gate "%s"' % tap.GetName())
      ret.append('  last activity: %s' % (meter.GetLastActivity(),))
      ret.append('   last reading: %s' % (meter.GetLastReading(),))
      ret.append('    total ticks: %s' % (meter.GetTicks(),))
      ret.append('')

  def GateExists(self, name):
    return name in self._gates

  def GetAllGates(self):
    return self._gates.values()

  def _CheckGateExists(self, name):
    if not self.GateExists(name):
      raise UnknownTapError

  def RegisterGate(self, name):
    self._logger.info('Registering new gate: %s' % name)
    if self.GateExists(name):
      raise AlreadyRegisteredError
    self._gates[name] = Gate(name)

  def UnregisterGate(self, name):
    self._logger.info('Unregistering gate: %s' % name)
    self._CheckGateExists(name)
    del self._gates[name]

  def GetGate(self, name):
    self._CheckGateExists(name)
    return self._gates[name]

  def UpdateDeviceReading(self, name, value):
    meter = self.GetGate(name).GetMeter()
    delta = meter.SetTicks(value)
    return delta

class Latch:
  def __init__(self, gate, latch_id, username=None, max_idle_secs=10):
    self._gate = gate
    self._latch_id = latch_id
    self._bound_username = username
    self._max_idle = datetime.timedelta(seconds=max_idle_secs)
    self._state = kbevent.LatchUpdate.LatchState.INITIAL
    self._start_time = datetime.datetime.now()
    self._end_time = None
    self._last_log_time = None

  def __str__(self):
    return '<Latch 0x%08x: gate=%s username=%s max_idle=%s>' % (self._latch_id,
        self._gate, repr(self._bound_username), self._max_idle)

  def GetUpdateEvent(self):
    event = kbevent.LatchUpdate()
    event.latch_id = self._latch_id
    event.gate_name = self._gate.GetName()
    event.state = self._state

    # TODO(mikey): username or user_name in the proto, not both
    if self._bound_username:
      event.username = self._bound_username

    event.start_time = self._start_time
    end = self._start_time
    if self._end_time:
      end = self._end_time
    event.last_activity_time = end

    return event

  def GetId(self):
    return self._latch_id

  def GetState(self):
    return self._state

  def SetState(self, state):
    self._state = state

  def SetMaxIdle(self, max_idle_secs):
    self._max_idle = datetime.timedelta(seconds=max_idle_secs)

  def GetUsername(self):
    return self._bound_username

  def SetUsername(self, username):
    self._bound_username = username

  def GetStartTime(self):
    return self._start_time

  def GetEndTime(self):
    return self._end_time

  def GetIdleTime(self):
    end_time = self._end_time
    if end_time is None:
      end_time = self._start_time
    return datetime.datetime.now() - end_time

  def GetMaxIdleTime(self):
    return self._max_idle

  def GetGate(self):
    return self._gate

  def IsIdle(self):
    return self.GetIdleTime() > self.GetMaxIdleTime()


class LatchManager(Manager):
  """Class reponsible for maintaining and servicing flows.

  The manager is responsible for creating Flow instances and managing their
  lifecycle.  It is one layer above the the TapManager, in that it does not
  deal with devices directly.

  Flows can be started in multiple ways:
    - Explicitly, by a call to StartFlow
    - Implicitly, by a call to HandleTapActivity
  """
  def __init__(self, name, event_hub, gate_manager):
    Manager.__init__(self, name, event_hub)
    self._gate_manager = gate_manager
    self._latch_map = {}
    self._logger = logging.getLogger("latchmanager")
    self._next_latch_id = int(time.time())
    self._lock = threading.Lock()

  @util.synchronized
  def _GetNextLatchId(self):
    """Returns the next usable flow identifier.

    Flow IDs are simply sequence numbers, used around the core to disambiguate
    flows."""
    ret = self._next_latch_id
    self._next_latch_id += 1
    return ret

  def GetStatus(self):
    ret = []
    active_latches = self.GetActiveLatches()
    if not active_latches:
      ret.append('Active latches: None')
    else:
      ret.append('Active latches: %i' % len(active_latches))
      for latch in active_latches:
        ret.append('  Latch on gate %s' % latch.GetTap())
        ret.append('         username: %s' % latch.GetUsername())
        ret.append('       start time: %s' % latch.GetStartTime())
        ret.append('      last active: %s' % latch.GetEndTime())
        ret.append('')

    return ret

  def GetActiveLatches(self):
    return self._latch_map.values()

  def GetLatch(self, gate_name):
    return self._latch_map.get(gate_name)

  def StartLatch(self, gate_name, username='', max_idle_secs=10):
    try:
      gate = self._gate_manager.GetGate(gate_name)
    except UnknownGateError:
      return None

    current = self.GetLatch(gate_name)
    if current and username and current.GetUsername() != username:
      # There's an existing latch: take it over if anonymous; end it if owned by
      # another user.
      if current.GetUsername() == '':
        self._logger.info('User "%s" is taking over the existing latch' %
            username)
        self.SetUsername(current, username)
      else:
        self._logger.info('User "%s" is replacing the existing latch' %
            username)
        self.StopLatch(gate_name)
        current = None

    if current and current.GetUsername() == username:
      # Existing flow owned by this username.  Just poke it.
      current.SetMaxIdle(max_idle_secs)
      self._PublishUpdate(current)
      return current
    else:
      # No existing latch; start a new one.
      new_latch = Latch(gate, latch_id=self._GetNextLatchId(), username=username,
          max_idle_secs=max_idle_secs)
      self._latch_map[gate_name] = new_latch
      self._logger.info('Starting latch: %s' % new_latch)
      self._PublishUpdate(new_latch)
      return new_latch

  def SetUsername(self, latch, username):
    latch.SetUsername(username)
    self._PublishUpdate(latch)

  def StopLatch(self, gate_name):
    try:
      latch = self.GetLatch(gate_name)
    except UnknownGateError:
      return None
    if not latch:
      return None

    self._logger.info('Stopping latch: %s' % latch)
    gate = latch.GetGate()
    del self._latch_map[gate_name]
    self._StateChange(latch, kbevent.LatchUpdate.LatchState.COMPLETED)
    return latch

  def UpdateLatch(self, gate_name, meter_reading):
    try:
      gate = self._gate_manager.GetGate(gate_name)
    except GateManagerError:
      # gate is unknown or not available
      # TODO(mikey): guard against this happening
      return None, None

    delta = self._gate_manager.UpdateDeviceReading(gate.GetName(), meter_reading)
    self._logger.debug('Flow update: tap=%s meter_reading=%i (delta=%i)' %
        (gate_name, meter_reading, delta))

    if delta == 0:
      return None, None

    is_new = False
    latch = self.GetLatch(gate_name)
    if latch is None:
      self._logger.debug('Starting flow implicitly due to activity.')
      latch = self.StartLatch(gate_name)
      is_new = True

    if latch.GetState() != kbevent.LatchUpdate.LatchState.ACTIVE:
      self._StateChange(latch, kbevent.LatchUpdate.LatchState.ACTIVE)
    else:
      self._PublishUpdate(latch)

    return latch, is_new

  def _StateChange(self, latch, new_state):
    latch.SetState(new_state)
    self._PublishUpdate(latch)

  def _PublishUpdate(self, latch):
    event = latch.GetUpdateEvent()
    self._PublishEvent(latch)

  @EventHandler(kbevent.HeartbeatSecondEvent)
  def _HandleHeartbeatEvent(self, event):
    for latch in self.GetActiveLatches():
      if latch.IsIdle():
        self._logger.info('Latch has become too idle, ending: %s' % latch)
        self._StateChange(latch, kbevent.LatchUpdate.LatchState.IDLE)
        self.StopLatch(latch.GetGate().GetName())

  @EventHandler(kbevent.LatchRequest)
  def _HandleLatchRequestEvent(self, event):
    if event.request == event.Action.START_LATCH:
      self.StartLatch(event.gate_name)
    elif event.request == event.Action.STOP_LATCH:
      self.StopLatch(event.gate_name)


class TokenRecord:
  STATUS_ACTIVE = 'active'
  STATUS_REMOVED = 'removed'

  def __init__(self, auth_device, token_value, gate_name):
    self.auth_device = auth_device
    self.token_value = token_value
    self.gate_name = gate_name
    self.last_seen = datetime.datetime.now()
    self.status = self.STATUS_ACTIVE

  def __str__(self):
    return '%s=%s@%s' % self.AsTuple()

  def AsTuple(self):
    return (self.auth_device, self.token_value, self.gate_name)

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
  def __init__(self, name, event_hub, latch_manager, gate_manager, backend):
    Manager.__init__(self, name, event_hub)
    self._latch_manager = latch_manager;
    self._gate_manager = gate_manager
    self._backend = backend
    self._tokens = {}  # maps tap name to currently active token
    self._lock = threading.RLock()

  @EventHandler(kbevent.TokenAuthEvent)
  def HandleAuthTokenEvent(self, event):
    for gate in self._GetGatesForGateName(event.gate_name):
      record = self._GetRecord(event.auth_device_name, event.token_value,
          gate.GetName())
      if event.status == event.TokenState.ADDED:
        self._TokenAdded(record)
      else:
        self._TokenRemoved(record)

  def _GetRecord(self, auth_device, token_value, gate_name):
    new_rec = TokenRecord(auth_device, token_value, gate_name)
    existing = self._tokens.get(gate_name)
    if new_rec == existing:
      return existing
    return new_rec

  def _MaybeStartFlow(self, record):
    """Called when the given token has been added.

    This will either start or renew a flow on the FlowManager."""
    username = None
    gate_name = record.gate_name
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
    self._latch_manager.StartLatch(gate_name, username=username,
        max_idle_secs=max_idle)

  def _MaybeEndFlow(self, record):
    """Called when the given token has been removed.

    If the auth device is a captive auth device, then this will forcibly end the
    flow.  Otherwise, this is a no-op."""
    is_captive = kb_common.AUTH_DEVICE_CAPTIVE.get(record.auth_device)
    if is_captive is None:
      is_captive = kb_common.AUTH_DEVICE_CAPTIVE['default']
    if is_captive:
      self._logger.debug('Captive auth device, ending flow immediately.')
      self._latch_manager.StopLatch(record.gate_name)
    else:
      self._logger.debug('Non-captive auth device, not ending flow.')

  @util.synchronized
  def _TokenAdded(self, record):
    """Processes a record when a token is added."""
    self._logger.info('Token attached: %s' % record)
    existing = self._tokens.get(record.gate_name)

    if existing == record:
      # Token is already known; nothing to do except update it.
      record.UpdateLastSeen()
      return

    if existing:
      self._logger.info('Removing previous token')
      self._TokenRemoved(existing)

    self._tokens[record.gate_name] = record
    self._MaybeStartFlow(record)

  @util.synchronized
  def _TokenRemoved(self, record):
    self._logger.info('Token detached: %s' % record)
    if record != self._tokens.get(record.gate_name):
      self._logger.warning('Token has already been removed')
      return

    record.SetStatus(record.STATUS_REMOVED)
    del self._tokens[record.gate_name]
    self._MaybeEndFlow(record)

  def _GetGatesForGateName(self, gate_name):
    if gate_name == kb_common.ALIAS_ALL_GATES:
      return self._gate_manager.GetAllGates()
    else:
      if self._gate_manager.GateExists(gate_name):
        return [self._gate_manager.GetGate(gate_name)]
      else:
        return []


class SubscriptionManager(Manager):
  def __init__(self, name, event_hub, server):
    Manager.__init__(self, name, event_hub)
    self._server = server
  @EventHandler(kbevent.CreditAddedEvent)
  @EventHandler(kbevent.DrinkCreatedEvent)
  @EventHandler(kbevent.LatchUpdate)
  def RepostEvent(self, event):
    self._server.SendEventToClients(event)
