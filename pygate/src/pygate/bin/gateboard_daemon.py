#!/usr/bin/env python
#
# Copyright 2009 Mike Wakerly <opensource@hoho.com>
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

"""Gateboard daemon.

The gateboard daemon is the primary interface between a gateboard devices and a
kegbot system.  The process is responsible for several tasks, including:
  - discovering gateboards available locally
  - connecting to the kegbot core and registering the individual boards
  - accumulating data if the kegbot core is offline

The gateboard daemon is compatible with any device that speaks the gateboard
Serial Protocol. See http://kegbot.org/docs for the complete specification.

The daemon should run on any machine which is attached to gateboard hardware.

The daemon must connect to a Kegbot Core in order to publish data (such as flow
and temperature events).  This is a TCP connection, using the Kegnet Protocol to
exchange data.
"""

import Queue

import gflags
import serial
import time

from pygate.core import importhacks
from pygate.core import kb_app
from pygate.core import kb_common
from pygate.core import util
from pygate.core.net import gatenet
from pygate.hw.gateboard import gateboard

FLAGS = gflags.FLAGS

gflags.DEFINE_string('gateboard_name', 'gateboard',
    'Name of this gateboard that will be used when talking to the core. '
    'If you are using multiple gateboards, you will want to run different '
    'daemons with different names. Otherwise, the default is fine.')

gflags.DEFINE_boolean('show_messages', True,
    'Print all messages going to and from the gateboard. Useful for '
    'debugging.')

gflags.DEFINE_integer('required_firmware_version', 4,
    'Minimum firmware version required.  If the device has an older '
    'firmware version, the daemon will refuse to service it.  This '
    'value should probably not be changed.')

FLAGS.SetDefault('tap_name', kb_common.ALIAS_ALL_GATES)

class KegboardKegnetClient(gatenet.SimpleKegnetClient):
  pass

class KegboardManagerApp(kb_app.App):
  def __init__(self, name='core'):
    kb_app.App.__init__(self, name)

  def _Setup(self):
    kb_app.App._Setup(self)

    self._client = KegboardKegnetClient()

    self._client_thr = gatenet.KegnetClientThread('gatenet', self._client)
    self._AddAppThread(self._client_thr)

    self._manager_thr = KegboardManagerThread('gateboard-manager',
        self._client)
    self._AddAppThread(self._manager_thr)

    self._device_io_thr = KegboardDeviceIoThread('device-io', self._manager_thr,
        FLAGS.gateboard_device, FLAGS.gateboard_speed)
    self._AddAppThread(self._device_io_thr)


class KegboardManagerThread(util.GatebotThread):
  """Manager of local gateboard devices."""

  def __init__(self, name, client):
    util.GatebotThread.__init__(self, name)
    self._client = client
    self._message_queue = Queue.Queue()

  def _DeviceName(self, base_name):
    return '%s.%s' % (FLAGS.gateboard_name, base_name)

  def PostDeviceMessage(self, device_name, device_message):
    """Receive a message from a device, for processing."""
    self._message_queue.put((device_name, device_message))

  def run(self):
    self._logger.info('Starting main loop.')
    initialized = False

    while not self._quit:
      try:
        device_name, device_message = self._message_queue.get(timeout=1.0)
      except Queue.Empty:
        continue

      if FLAGS.show_messages:
        self._logger.info('RX: %s' % str(device_message))
      self._HandleDeviceMessage(device_name, device_message)

    self._logger.info('Exiting main loop.')

  def _HandleDeviceMessage(self, device_name, msg):
    if isinstance(msg, gateboard.OnewirePresenceMessage):
      strval = '%016x' % msg.device_id
      if msg.status == 1:
        self._client.SendAuthTokenAdd(FLAGS.tap_name,
            kb_common.AUTH_MODULE_CORE_ONEWIRE, strval)
      else:
        self._client.SendAuthTokenRemove(FLAGS.tap_name,
            kb_common.AUTH_MODULE_CORE_ONEWIRE, strval)

    elif isinstance(msg, gateboard.AuthTokenMessage):
      # For legacy reasons, a gateboard-reported device name of 'onewire' is
      # translated to 'core.onewire'. Any other device names are reported
      # verbatim.
      device = msg.device
      if device == 'onewire':
        device = kb_common.AUTH_MODULE_CORE_ONEWIRE

      # Convert the token byte field to little endian string representation.
      bytes_be = msg.token
      bytes_le = ''
      for b in bytes_be:
        bytes_le = '%02x%s' % (ord(b), bytes_le)

      if msg.status == 1:
        self._client.SendAuthTokenAdd(FLAGS.tap_name, device, bytes_le)
      else:
        self._client.SendAuthTokenRemove(FLAGS.tap_name, device, bytes_le)


class KegboardDeviceIoThread(util.GatebotThread):
  """Manages all device I/O.

  This thread continuously reads from attached gateboard devices and passes
  messages to the KegboardManagerThread.
  """
  def __init__(self, name, manager, device_path, device_speed):
    util.GatebotThread.__init__(self, name)
    self._manager = manager
    self._device_path = device_path
    self._device_speed = device_speed
    self._reader = None
    self._serial_fd = None

  def _SetupSerial(self):
    self._logger.info('Setting up serial port...')
    self._serial_fd = serial.Serial(self._device_path, self._device_speed)
    self._reader = gateboard.KegboardReader(self._serial_fd)

  def run(self):
    self._SetupSerial()
    try:
      self._MainLoop()
    finally:
      self._serial_fd.close()

  def Ping(self):
    ping_message = gateboard.PingCommand()
    self._reader.WriteMessage(ping_message)

  def _MainLoop(self):
    self._logger.info('Starting reader loop...')

    # Ping the board a couple of times before going into the listen loop.
    for i in xrange(2):
      self.Ping()

    initialized = False
    while not self._quit:
      try:
        msg = self._reader.GetNextMessage()
      except gateboard.UnknownMessageError:
        self._logger.warning('Read unknown message, skipping')
        continue

      # Check the reported firmware version. If it is not acceptable, then
      # drop all messages until it is updated.
      # TODO(mikey): kill the application when this happens? It isn't strictly
      # necessary, but is probably the most obvious way to get the point across.
      if isinstance(msg, gateboard.HelloMessage):
        version = msg.firmware_version
        if version >= FLAGS.required_firmware_version:
          if not initialized:
            self._logger.info('Found a Gateboard! Firmware version %i' % version)
            initialized = True
        else:
          self._logger.error('Attached gateboard firmware version (%s) is '
              'less than the required version (%s); please update this '
              'gateboard.' % (actual, required))
          self._logger.warning('Messages from this board will be ignored '
              'until it is updated.')
          initialized = False

      if not initialized:
        self.Ping()
        time.sleep(0.1)
        continue

      self._manager.PostDeviceMessage('gateboard', msg)
    self._logger.info('Reader loop ended.')


if __name__ == '__main__':
  KegboardManagerApp.BuildAndRun()
