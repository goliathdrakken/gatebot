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

"""Kegweb API client."""

import datetime
import functools
import socket
import sys
import types

from pygate.core import kbjson

try:
  from urllib.parse import urlencode
  from urllib.request import urlopen
  from urllib.error import HTTPError
  from urllib.error import URLError
except ImportError:
  from urllib import urlencode
  from urllib2 import urlopen
  from urllib2 import HTTPError
  from urllib2 import URLError

import gflags
FLAGS = gflags.FLAGS

_DEFAULT_URL = 'http://localhost:8000/api/'
_DEFAULT_KEY = ''
try:
  from pygate import settings
  if hasattr(settings, 'KEGWEB_BASE_URL'):
    _DEFAULT_URL = '%s/api' % getattr(settings, 'KEGWEB_BASE_URL')
  if hasattr(settings, 'KEGWEB_API_KEY'):
    _DEFAULT_KEY = settings.KEGWEB_API_KEY
except ImportError:
  # Non-fatal if we can't load settings.
  pass

gflags.DEFINE_string('api_url', _DEFAULT_URL,
    'Base URL for the Kegweb HTTP api.')

gflags.DEFINE_string('api_key', _DEFAULT_KEY,
    'Access key for the Kegweb HTTP api.')

### begin common

class Error(Exception):
  """An error occurred."""
  HTTP_CODE = 400
  def Message(self):
    if self.message:
      return self.message
    m = self.__class__.__doc__
    m = m.split('\n', 1)[0]
    return m

class NotFoundError(Error):
  """The requested object could not be found."""
  HTTP_CODE = 404

class ServerError(Error):
  """The server had a problem fulfilling your request."""
  HTTP_CODE = 500

class BadRequestError(Error):
  """The request was incompleted or malformed."""
  HTTP_CODE = 401

class NoAuthTokenError(Error):
  """An api_auth_token is required."""
  HTTP_CODE = 401

class BadAuthTokenError(Error):
  """The api_auth_token given is invalid."""
  HTTP_CODE = 401

class PermissionDeniedError(Error):
  """The api_auth_token given does not have permission for this resource."""
  HTTP_CODE = 401

MAP_NAME_TO_EXCEPTION = dict((c.__name__, c) for c in Error.__subclasses__())

def ErrorCodeToException(code, message=None):
  cls = MAP_NAME_TO_EXCEPTION.get(code, Error)
  return cls(message)

### end common

class KrestClient:
  """Kegweb RESTful API client."""
  def __init__(self, api_url=None, api_key=None):
    if api_url is None:
      api_url = FLAGS.api_url
    if api_key is None:
      api_key = FLAGS.api_key
    self._api_url = api_url
    self._api_auth_token = api_key

  def _Encode(self, s):
    return unicode(s).encode('utf-8')

  def _EncodePostData(self, post_data):
    if not post_data:
      return None
    return urlencode(dict(((k, self._Encode(v)) for k, v in
        post_data.iteritems() if v is not None)))

  def _GetURL(self, endpoint, params=None):
    param_str = ''
    if params:
      param_str = '?%s' % urlencode(params)

    base = self._api_url.rstrip('/')

    # Strip both leading and trailing slash from endpoint: single leading and
    # trailing slashes will be added by the string formatter.  (The trailing
    # slash is required for POSTs to Django.)
    endpoint = endpoint.strip('/')
    return '%s/%s/%s' % (base, endpoint, param_str)

  def SetAuthToken(self, api_auth_token):
    self._api_auth_token = api_auth_token

  def DoGET(self, endpoint, params=None):
    """Issues a GET request to the endpoint, and retuns the result.

    Keyword arguments are passed to the endpoint as GET arguments.

    For normal responses, the return value is the Python JSON-decoded 'result'
    field of the response.  If the response is an error, a RemoteError exception
    is raised.

    If there was an error contacting the server, or in parsing its response, a
    ServerError is raised.
    """
    return self._FetchResponse(endpoint, params=params)

  def DoPOST(self, endpoint, post_data, params=None):
    """Issues a POST request to the endpoint, and returns the result.

    For normal responses, the return value is the Python JSON-decoded 'result'
    field of the response.  If the response is an error, a RemoteError exception
    is raised.

    If there was an error contacting the server, or in parsing its response, a
    ServerError is raised.
    """
    return self._FetchResponse(endpoint, params=params, post_data=post_data)

  def _FetchResponse(self, endpoint, params=None, post_data=None):
    """Issues a POST or GET request, depending on the arguments."""
    if params is None:
      params = {}
    else:
      params = params.copy()

    # If we have an api token, attach it.  Prefer to attach it to POST data, but
    # use GET if there is no POST data.
    if self._api_auth_token:
      if post_data:
        post_data['api_auth_token'] = self._api_auth_token
      else:
        params['api_auth_token'] = self._api_auth_token

    url = self._GetURL(endpoint, params=params)
    encoded_post_data = self._EncodePostData(post_data)

    try:
      # Issue a GET or POST (urlopen will decide based on encoded_post_data).
      response_data = urlopen(url, encoded_post_data).read()
    except HTTPError, e:
      raise ServerError('Caused by: %s' % e)
    except URLError, e:
      raise e.reason

    return self._DecodeResponse(response_data)

  def _DecodeResponse(self, response_data):
    """Decodes the string `response_data` as a JSON response.

    For normal responses, the return value is the Python JSON-decoded 'result'
    field of the response.  If the response is an error, a RemoteError exception
    is raised.
    """
    # Decode JSON.
    try:
      d = kbjson.loads(response_data)
    except ValueError, e:
      raise ServerError('Malformed response: %s' % e)

    if 'error' in d:
      # Response had an error: translate to exception.
      err = d.get('error')
      if type(err) != types.DictType:
        raise ValueError('Invalid error response from server')
      code = err.get('code', 'Error')
      message = err.get('message', None)
      e = ErrorCodeToException(code, message)
      raise e
    elif 'result' in d:
      # Response was OK, return the result.
      return d.get('result')
    else:
      # WTF?
      raise ValueError('Invalid response from server: missing result or error')

  def RecordEntry(self, gate_name, username=None, pour_time=None,
      duration=0, auth_token=None):
    endpoint = '/gate/%s' % gate_name
    post_data = {
      'gate_name': gate_name,
      'username': username,
      'auth_token': auth_token,
      'duration': duration,
    }
    if pour_time:
      post_data['pour_time'] = int(pour_time.strftime('%s'))
      post_data['now'] = int(datetime.datetime.now().strftime('%s'))
    return self.DoPOST(endpoint, post_data=post_data)

  def CancelEntry(self, seqn):
    endpoint = '/cancel-entry'
    post_data = {
      'id': seqn,
    }
    return self.DoPOST(endpoint, post_data=post_data)

  def GateStatus(self):
    """Gets the status of all taps."""
    return self.DoGET('tap')

  def GetToken(self, auth_device, token_value):
    url = 'auth-token/%s.%s' % (auth_device, token_value)
    try:
      return self.DoGET(url)
    except ServerError, e:
      raise NotFoundError(e)

  def LastEntry(self):
    """Gets a list of the most recent drinks."""
    return self.DoGET('last-entries')

  def AllEntries(self):
    """Gets a list of all entries."""
    return self.DoGET('entry')

  def AllSoundEvents(self):
    """Gets a list of all drinks."""
    return self.DoGET('sound-event')


def main():
  c = KrestClient()

  print '== record a drink =='
  print c.RecordEntry('kegboard.flow0')
  print ''

  print '== tap status =='
  for t in c.GateStatus():
    print t
    print ''

  print '== last drinks =='
  for d in c.LastEntries():
    print d
    print ''

if __name__ == '__main__':
  FLAGS(sys.argv)
  main()
