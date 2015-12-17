SMASHCache
==========

A caching reverse proxy built to deal with video files.

As other proxies seemed to want to grab the file from the
start and get the whole thing before serving a range-request
this was born.  Grabs the closest chunk and feeds it.  Built
to deal with upstream dropping video files from cache for infrequent
access and then serving slowly, first user would hit this slowly,
then future access would be fast, served from our host.  Boxes
running this software would be throw-away.


Warning
-------

This project is abandoned.

The code was thrown together to fit a purpose quickly as
possible.
The code is terribly messy and bad, and could probably get
a box owned.


Configure
---------

Configure it by looking at smashcache/cache/cache.py
