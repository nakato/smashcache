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

import requests


def getHeaders(url):
    r = requests.head(url)
    if r.status_code != 200:
        print("Server returned" + r.status_code)
        return None
    return r.headers


def fetchRangeToFile(url, byte_range, destination_path):
    print("Fetching: %s range: %s to: %s" %
          (url, byte_range, destination_path))
    headers = {'Range': ("bytes=%s-%s" %
               (byte_range[0], byte_range[1]))}
    r = requests.get(url, headers=headers, stream=True)
    with open(destination_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                f.flush()
