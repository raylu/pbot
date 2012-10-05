#!/usr/bin/env python3

import config

import sys
if sys.argv[-1] == '-d':
	from daemon import daemonize
	daemonize()

import log
from bot import Bot

import select

epoll = select.epoll()
EPOLLFLAGS = select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP

fds = {}
for c in config.bots:
	if not c.autoconnect:
		continue
	bot = Bot(c)
	fd = bot.conn.socket.fileno()
	fds[fd] = bot
	epoll.register(fd, EPOLLFLAGS)

try:
	while True:
		results = epoll.poll()
		for fd, flags in results:
			bot = fds[fd]
			bot.handle()
		log.flush()
except KeyboardInterrupt:
	for b in fds.values():
		b.disconnect()
finally:
	epoll.close()
	log.close()
