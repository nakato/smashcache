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

import re
from smashcache.cache import cache
from smashcache.pages import errors


byte_range_re = re.compile('^bytes=(\d+)?\-(\d+)?$')

c = cache.Cache()


def application(environ, start_response):
    request_method = environ.get('REQUEST_METHOD')
    path = environ.get('PATH_INFO')
    response_body = [b'']
    response_headers = []
    response_headers.extend([('Accept-Ranges', 'bytes')])
    try:
        response_headers.extend(c.headers(path))
    except errors.HTTPError as e:
        status = e.status
        response_headers = e.response_headers
        start_response(status, response_headers)
        return e.response_body
    if request_method == "HEAD":
        try:
            response_headers.extend(c.headersContentLength(path))
        except errors.HTTPError as e:
            status = e.status
            response_headers = e.response_headers
            start_response(status, response_headers)
            return e.response_body
        status = "200 OK"
    elif request_method == "GET":
        if 'HTTP_RANGE' in environ:
            byte_range = environ.get('HTTP_RANGE')
            r = byte_range_re.match(byte_range)
            if r == None:
               e = errors.error400()
               status = e.status
               response_headers = e.response_headers
               start_response(status, response_headers)
               return e.response_body
            byte_start = r.group(1)
            byte_end = r.group(2)
        else:
            byte_start = 0
            byte_end = None
        if byte_start != None:
            byte_start = int(byte_start)
        else:
            byte_start = 0
        if byte_end != None:
            byte_end = int(byte_end)
        if byte_start == 0:
            status = "200 OK"
        else:
            status = "206 Partial Content"
        try:
            response_body = c.getIterator(path, response_headers, byte_start,
                                          byte_end)
        except errors.HTTPError as e:
            status = e.status
            response_headers = e.response_headers
            start_response(status, response_headers)
            return e.response_body
    else:
        status = "501 NOT IMPLEMENTED"
        response_headers = []
    start_response(status, response_headers)
    return response_body
