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
    self.test_token_2 = self.backend.CreateAuthToken('core.onewire',
        'baadcafebeeff00d', 'tester_2')
    kb_common.AUTH_TOKEN_MAX_IDLE['core.onewire'] = 2

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
    # Synthesize a 2200-tick flow. The FlowManager should zero on the initial
    # reading of 1000.
    meter_name = self.test_gate.meter_name
    self.client.SendLatchStart(meter_name)
    self.client.SendMeterUpdate(meter_name, 1000)

    self.client.SendLatchStop(meter_name)
    self.service_thread._FlushEvents()

    drinks = self.test_keg.entries.valid()
    self.assertEquals(len(drinks), 1)
    last_entry = drinks[0]

    LOGGER.info('last drink: %s' % (last_entry,))
    self.assertEquals(last_drink.ticks, 2200)

    self.assertEquals(last_drink.keg, self.test_keg)

    self.assertEquals(last_drink.user, None)

  def testAuthenticatedLatch(self):
    meter_name = self.test_gate.meter_name

    # Start a flow by pouring a few ticks.
    self.client.SendMeterUpdate(meter_name, 100)
    self.client.SendMeterUpdate(meter_name, 200)
    time.sleep(1.0)
    self.service_thread._FlushEvents()

    # The flow should be anonymous, since no user is authenticated.
    flow_mgr = self.env.GetFlowManager()
    latches = flow_mgr.GetActiveFlows()
    self.assertEquals(len(flows), 1)
    latch = latches[0]
    self.assertEquals(latch.GetUsername(), '')

    # Now authenticate the user.
    # TODO(mikey): should use tap name rather than meter name.
    self.client.SendAuthTokenAdd(self.test_gate.meter_name,
        auth_device_name=self.test_token.auth_device,
        token_value=self.test_token.token_value)
    time.sleep(1.0) # TODO(mikey): need a synchronous wait
    self.service_thread._FlushEvents()
    self.assertEquals(latch.GetUsername(), self.test_user.username)

    # If another user comes along, he takes over the flow.
    self.client.SendAuthTokenAdd(self.test_gate.meter_name,
        auth_device_name=self.test_token_2.auth_device,
        token_value=self.test_token_2.token_value)
    time.sleep(1.0) # TODO(mikey): need a synchronous wait
    self.service_thread._FlushEvents()

    latches = flow_mgr.GetActiveFlows()
    self.assertEquals(len(latches), 1)
    latch = latches[0]
    self.assertEquals(latch.GetUsername(), self.test_user_2.username)

    self.client.SendMeterUpdate(meter_name, 300)
    time.sleep(1.0) # TODO(mikey): need a synchronous wait
    self.service_thread._FlushEvents()
    self.client.SendLatchStop(meter_name)
    time.sleep(1.0) # TODO(mikey): need a synchronous wait
    self.service_thread._FlushEvents()

    drinks = self.test_gate.entries.valid().order_by('id')
    self.assertEquals(len(drinks), 2)
    self.assertEquals(protolib.ToProto(entries[0].user), self.test_user)
    self.assertEquals(protolib.ToProto(entries[1].user), self.test_user_2)

  def testIdleFlow(self):
    meter_name = self.test_gate.meter_name
    self.client.SendLatchStart(meter_name)
    self.client.SendMeterUpdate(meter_name, 0)
    self.client.SendMeterUpdate(meter_name, 100)
    time.sleep(1.0)
    self.service_thread._FlushEvents()

    flows = self.env.GetLatchManager().GetActiveLatches()
    self.assertEquals(len(flows), 1)

    # Rewind the flow activity clocks to simulate idleness.
    flows[0]._start_time -= datetime.timedelta(minutes=10)
    flows[0]._end_time = flows[0]._start_time

    # Wait for the heartbeat event to kick in.
    time.sleep(1.0)
    self.service_thread._FlushEvents()

    # Verify that the flow has been ended.
    latches = self.env.GetLatchManager().GetActiveLatches()
    self.assertEquals(len(flows), 0)

  def testTokenDebounce(self):
    meter_name = self.test_tap.meter_name
    self.client.SendFlowStart(meter_name)
    self.client.SendMeterUpdate(meter_name, 0)
    self.client.SendMeterUpdate(meter_name, 100)
    time.sleep(1.0)
    self.service_thread._FlushEvents()

    self.client.SendAuthTokenAdd(self.test_tap.meter_name,
        auth_device_name=self.test_token.auth_device,
        token_value=self.test_token.token_value)
    time.sleep(1.0) # TODO(mikey): need a synchronous wait
    self.service_thread._FlushEvents()

    flows = self.env.GetFlowManager().GetActiveFlows()
    self.assertEquals(len(flows), 1)
    flow = flows[0]
    self.assertEquals(flow.GetUsername(), self.test_user.username)
    original_flow_id = flow.GetId()

    LOGGER.info('Removing token...')
    self.client.SendAuthTokenRemove(self.test_tap.meter_name,
        auth_device_name=self.test_token.auth_device,
        token_value=self.test_token.token_value)
    time.sleep(0.5)
    self.service_thread._FlushEvents()

    # The flow should still be active.
    flows = self.env.GetFlowManager().GetActiveFlows()
    self.assertEquals(len(flows), 1)
    flow = flows[0]
    self.assertEquals(flow.GetId(), original_flow_id)
    self.assertEquals(flow.GetState(), kbevent.FlowUpdate.FlowState.ACTIVE)

    # Re-add the token; should be unchanged.
    self.client.SendAuthTokenAdd(self.test_tap.meter_name,
        auth_device_name=self.test_token.auth_device,
        token_value=self.test_token.token_value)
    time.sleep(0.5)
    self.service_thread._FlushEvents()

    # No change in flow
    flows = self.env.GetFlowManager().GetActiveFlows()
    self.assertEquals(len(flows), 1)
    flow = flows[0]
    self.assertEquals(flow.GetId(), original_flow_id)
    self.assertEquals(flow.GetState(), kbevent.FlowUpdate.FlowState.ACTIVE)

    # Idle out. TODO(mikey): shift clock instead of sleeping.
    time.sleep(2.5)
    self.service_thread._FlushEvents()
    flows = self.env.GetFlowManager().GetActiveFlows()
    self.assertEquals(len(flows), 0)

if __name__ == '__main__':
  unittest.main()
