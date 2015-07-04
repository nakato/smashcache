# Copyright (c) 2015 Sachi King
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


class HTTPError(Exception):
    """Base Error class for all HTTP errors"""

    pass


class error500(HTTPError):
    """Return a simple 500 to the client trapping the error"""

    status = "500 Internal Server Error"
    response_headers = []
    response_body = [b'']


class error502(HTTPError):
    """Return a simple 502 to the client trapping the error"""

    status = "502 Bad Gateway"
    response_headers = []
    response_body = [b'']


class error404(HTTPError):
    """Return a 404 to the user"""

    status = "404 Not Found"
    response_headers = []
    response_body = [b'']


class error400(HTTPError):
    """Return a 400 to the user"""

    status = "400 Invalid Request"
    response_headers = []
    response_body = [b'']
