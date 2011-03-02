#!/usr/bin/env python
#
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

"""A simple HTTP server that proxies informaton to and from Gatenet."""

from pygate.core import importhacks

import cgi
import httplib
import gflags
import logging
import os
import time
from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer

from pygate.core import kbjson
from pygate.core import kb_app
from pygate.core import kb_common
from pygate.core import util
from pygate.core.net import gatenet

FLAGS = gflags.FLAGS

gflags.DEFINE_string('http_addr', '0.0.0.0:9900',
    'Host:port for binding the HTTP server.')

FLAGS.SetDefault('gate_name', kb_common.ALIAS_ALL_GATES)

class ProxyGatenetClient(gatenet.SimpleGatenetClient):
  def __init__(self, addr=None):
    gatenet.SimpleGatenetClient.__init__(self, addr)
    self.flows = {}

  def onFlowUpdate(self, event):
    self.flows[event.gate_name] = event

class ProxyServer(HTTPServer):
  def __init__(self, client):
    self._addr = util.str_to_addr(FLAGS.http_addr)
    self._logger = logging.getLogger('proxy-http')
    self.client = client
    HTTPServer.__init__(self, self._addr, ProxyRequestHandler)


class ProxyRequestHandler(BaseHTTPRequestHandler):
  def _ExtractParams(self):
    """Extract HTTP GET parameters from path."""
    self.params = {}
    self.callback = ''
    qpos = self.path.find('?')
    if qpos >= 0:
      self.params = cgi.parse_qs(self.path[qpos+1:], keep_blank_values=1)
      self.path = self.path[:qpos]
      if 'callback' in self.params:
        self.callback = self.params.get('callback')[0]
        del self.params['callback']

  def log_request(self, code='-', size='-'):
    client_addr = '%s:%i' % self.client_address
    msg = ' '.join(map(str, (code, client_addr, self.command, self.path)))
    self.server._logger.debug(msg)

  def do_GET(self):
    self._ExtractParams()
    client = self.server.client
    result = {
      'ok': False,
    }
    username = self.params.get('username')
    if username:
      username = username[0]
    if self.path == '/add' and username:
      self.server._logger.info('adding: %s' % username)
      client.SendAuthTokenAdd(FLAGS.gate_name, 'core.user', username)
      result['ok'] = True
    elif self.path == '/remove' and username:
      self.server._logger.info('removing: %s' % username)
      client.SendAuthTokenRemove(FLAGS.gate_name, 'core.user', username)
      result['ok'] = True
    elif self.path == '/flows':
      result['ok'] = True
      flow_dict = dict((k, v.ToDict()['data']) for k, v in self.server.client.flows.iteritems())
      result['flows'] = flow_dict
    elif self.path == '/status':
      result['ok'] = True
    return self._DoResponse(body=kbjson.dumps(result), type="application/json")

  def _DoResponse(self, body=None, code=httplib.OK, type="text/plain"):
    if code != httplib.OK and body is None:
      body = '%s %s' % (code, httplib.responses[code])
    self.send_response(code)
    self.send_header("Content-type", type)
    self.send_header("Content-length", len(body))
    self.end_headers()
    self.wfile.write(body)


class HttpThread(util.GatebotThread):
  def __init__(self, client):
    util.GatebotThread.__init__(self, 'proxy-http-thr')
    self.http_server = ProxyServer(client)

  def ThreadMain(self):
    self.http_server.serve_forever()


class ProxyApp(kb_app.App):
  def _Setup(self):
    kb_app.App._Setup(self)

    self._logger.info('Setting up gatenet client ...')

    self._client = ProxyGatenetClient()
    self._client_thr = gatenet.GatenetClientThread('gatenet', self._client)
    self._AddAppThread(self._client_thr)

    self._http_thread = HttpThread(self._client)
    self._AddAppThread(self._http_thread)


if __name__ == '__main__':
  ProxyApp.BuildAndRun()

