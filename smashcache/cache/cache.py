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

import eventlet
import math
import os
import re

#from oslo_config import cfg
from smashcache.cache import filler
from smashcache.pages import errors

opts = [
    cfg.StrOpt('chunk_storage_path',
               default='/tmp/smashcache',
               help="Location to download chunked target data"),
    cfg.IntOpt('chunk_size',
               default=8,
               help="Size in megabytes to chunk at a time"),
    cfg.StrOpt('proxy_host_url',
               help="URL to remote host")
]

UNITS_Ki = 1024
UNITS_Mi = 1024 ** 2

#CONF = cfg.CONF
#CONF.register_opts(opts)
#CONF(project='smashcache', default_config_files=None)
# Yes commenting out in git... :(

# uwsgi, which I wanted to use, freaked out with oslo config, so fake it
class conf(object):
    chunk_storage_path = '/tmp/smashcache'
    chunk_size = 8
    proxy_host_url = 'http://s3.amz.com/place'

CONF = conf

CHUNKSIZE = CONF.chunk_size * UNITS_Mi


class CacheObject(object):
    """Storage of known objects"""

    path_file_re = re.compile('^\/(.+/)?(.+\..+)$')

    def __init__(self, object_uri):
        if not isinstance(object_uri, str):
            raise errors.error500()
        r = self.path_file_re.match(object_uri)
        if r:
            object_path = "" if r.group(1) is None else r.group(1)
            object_name = r.group(2)
        else:
            print("Invalid file name %s" % object_uri)
            raise errors.error404()
        self.origin_url = (CONF.proxy_host_url + object_uri)
        self._headerValues()
        self._ensurePathsExist(object_path)
        self.stored_object_path = ("%s/%s/%s" % (CONF.chunk_storage_path,
                                   object_path, object_name))
        self.total_chunks = math.ceil(self.object_size / CHUNKSIZE)
        self.last_chunk_size = (self.object_size -
                                (self.total_chunks - 1) * CHUNKSIZE)
        self.chunks = []
        self.chunk_load = []
        for _ in range(self.total_chunks):
            self.chunks.append(False)
            self.chunk_load.append(False)

    def _ensurePathsExist(self, object_path):
        # TODO: Directory transversal
        paths = ['']
        if object_path != '':
            paths.extend(object_path.strip('/').split('/'))
        path = CONF.chunk_storage_path
        for p in paths:
            path = ("%s/%s" % (path, p))
            if not os.path.exists(path):
                os.makedirs(path)

    def _headerValues(self):
        upstream_headers = filler.getHeaders(self.origin_url)
        self.object_size = int(upstream_headers.get('content-length'))
        self.content_type = upstream_headers.get('content-type')
        if not self.object_size:
            raise errors.error502()

    def getRangeIterable(self, byte_start, byte_end):
        initial_chunk = math.floor(byte_start / CHUNKSIZE)
        current_chunk = initial_chunk
        start_offset = byte_start - initial_chunk * CHUNKSIZE
        total_bytes = byte_end - byte_start
        remaining_bytes = total_bytes
        max_read_bytes = 256 * UNITS_Ki
        bytes_to_read = max_read_bytes
        while True:
            if remaining_bytes == 0:
                break
            self.getOrWaitChunk(current_chunk)
            with open(self._chunk_path(current_chunk), 'rb') as f:
                if current_chunk == initial_chunk:
                    f.seek(start_offset)
                while True:
                    if remaining_bytes < max_read_bytes:
                        bytes_to_read = remaining_bytes
                    read_bytes = f.read(bytes_to_read)
                    remaining_bytes -= len(read_bytes)
                    yield read_bytes
                    if len(read_bytes) != max_read_bytes:
                        current_chunk += 1
                        break

    def getOrWaitChunk(self, chunk_number):
        if not self.chunks[chunk_number] and not self.chunk_load[chunk_number]:
            self.chunk_load[chunk_number] = True
            self._fetchChunk(chunk_number)
            self.chunks[chunk_number] = True
        elif self.chunks[chunk_number]:
            pass
        elif self.chunk_load[chunk_number]:
            while not self.chunks[chunk_number]:
                eventlet.sleep()
        else:
            raise errors.error500()

    def _fetchChunk(self, chunk_number):
        byte_range = (chunk_number * CHUNKSIZE,
                      (chunk_number + 1) * CHUNKSIZE - 1)
        if self._validChunkExists(chunk_number):
            return
        filler.fetchRangeToFile(self.origin_url, byte_range,
                                self._chunk_path(chunk_number))

    def _validChunkExists(self, chunk_number):
        chunk_path = self._chunk_path(chunk_number)
        expected_size = CHUNKSIZE
        if chunk_number == self.total_chunks - 1:
            expected_size = self.last_chunk_size
        return (os.path.isfile(chunk_path) and
                os.path.getsize(chunk_path) == expected_size)

    def _chunk_path(self, chunk_number):
        return ("%s.%s" % (self.stored_object_path, chunk_number))


class Cache(object):

    def __init__(self):
        self.objects = {}

    def headers(self, uri):
        if uri not in self.objects.keys():
            self.objects[uri] = CacheObject(uri)
        return [('Content-Type', self.objects[uri].content_type)]

    def headersContentLength(self, uri):
        if uri not in self.objects.keys():
            self.objects[uri] = CacheObject(uri)
        return [('Content-Length', str(self.objects[uri].object_size))]

    def getIterator(self, uri, headers, start=0, end=None):
        if uri not in self.objects.keys():
            self.objects[uri] = CacheObject(uri)
        if not end or end > self.objects[uri].object_size:
            end = self.objects[uri].object_size
        if start > end:
            raise errors.error400()
        if start == 0 and end == self.objects[uri].object_size:
            content_length = self.objects[uri].object_size
        else:
            # Sigh, so because 0 is "send first byte" and there are 20 bytes
            # we're sending bytes 0-19.  If we tell chrome we are sending
            # 0-20, that's 21 bytes and chrome freaks and sends a load of RST
            #
            # Todo: Look into how I handle send bytes and try to make this
            # less of a case-by-case modification to headers.  It's confusing
            headers.extend([('Content-Range', ("bytes %s-%s/%s" %
                           (start, end-1, self.objects[uri].object_size)))])
            content_length = end - start
        headers.extend([('Content-Length', str(content_length))])
        return self.objects[uri].getRangeIterable(start, end)
