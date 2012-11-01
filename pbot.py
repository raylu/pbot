#!/usr/bin/env python3

import config

import sys
if sys.argv[-1] == '-d':
	from daemon import daemonize
	daemonize()

import log
from bot import Bot

import errno
import select
import signal
import time

epoll = select.epoll()
EPOLLFLAGS = select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP

keep_going = True
def quit(signum, frame):
	global keep_going
	keep_going = False
for s in [signal.SIGTERM, signal.SIGINT]:
	signal.signal(s, quit)
	signal.siginterrupt(s, False)

fds = {}
for c in config.bots:
	if not c.autoconnect:
		continue
	bot = Bot(c)
	fd = bot.connect()
	fds[fd] = bot
	epoll.register(fd, EPOLLFLAGS)

try:
	while keep_going:
		try:
			results = epoll.poll(config.EPOLL_TIMEOUT)
		except IOError as e:
			if e.errno == errno.EINTR and not keep_going:
				break
			raise
		flags = dict(results)
		ts = time.time()
		for fd, bot in fds.items():
			if flags.get(fd, 0) & select.EPOLLIN == select.EPOLLIN:
				bot.handle()
			else:
				if bot.check_disconnect(ts):
					del fds[fd]
					epoll.unregister(fd)
					fd = bot.connect()
					fds[fd] = bot
					epoll.register(fd, EPOLLFLAGS)
		log.flush()
	for b in fds.values():
		b.disconnect()
finally:
	epoll.close()
	log.close()
