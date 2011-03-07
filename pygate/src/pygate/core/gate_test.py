#!/usr/bin/env python

"""Unittest for gatebot module"""

import commands
import datetime
import time
import logging
import socket
import unittest
import gatebot

from django.test import TestCase

from pygate.core import defaults
from pygate.core import kbevent
from pygate.core import models
from pygate.core import kb_common
from pygate.core import units
from pygate.core.net import gatenet


LOGGER = logging.getLogger('unittest')

class GatebotTestCase(TestCase):
  def setUp(self):
    del logging.root.handlers[:]
    defaults.set_defaults()
    #defaults.gentestdata()

    models.Entry.objects.all().delete()

    self.site, _ = models.GatebotSite.objects.get_or_create(name='default')

    self.test_gate = models.Gate.objects.create(site=self.site,
        name='Test Gate')

    self.gatebot = gatebot.GatebotCoreApp()
    self.env = self.gatebot._env
    self.backend = self.env.GetBackend()

    self.test_user = self.backend.CreateNewUser('tester')
    self.test_token = self.backend.CreateAuthToken('core.onewire',
        '0000111122223333', 'tester')

    self.test_user_2 = self.backend.CreateNewUser('tester_2')
    self.test_token_2 = self.backend.CreateAuthToken('rfid',
        '1243136425', 'tester_2')
    kb_common.AUTH_DEVICE_MAX_IDLE_SECS['core.onewire'] = 2
    kb_common.AUTH_DEVICE_MAX_IDLE_SECS['rfid'] = 2

    # Kill the gatebot latch processing thread so we can single step it.
    self.service_thread = self.env._service_thread
    self.env._threads.remove(self.service_thread)

    self.gatebot._Setup()
    self.gatebot._StartThreads()

    self.client = gatenet.GatenetClient()
    while True:
      if self.client.Reconnect():
        break

  def tearDown(self):
    for thr in self.env.GetThreads():
      self.assert_(thr.isAlive(), "thread %s died unexpectedly" % thr.getName())
    self.gatebot.Quit()
    for thr in self.env.GetThreads():
      self.assert_(not thr.isAlive(), "thread %s stuck" % thr.getName())
    del self.gatebot
    del self.env

  def testSimpleFlow(self):
    gate_name = self.test_gate.name
    self.client.SendOpenLatch(gate_name)

    self.client.SendCloseLatch(gate_name)
    self.service_thread._FlushEvents()

    entries = models.Entry.objects.all()
    self.assertEquals(len(entries), 1)
    last_entry = entries[0]

    LOGGER.info('last entry: %s' % (last_entry,))

    self.assertEquals(last_entry.user, None)

