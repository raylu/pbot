#!/usr/bin/env python3.4

import config

import sys
if sys.argv[-1] == '-d':
	from daemon import daemonize
	daemonize()

import log
from bot import Bot
import commands

import asyncio
import errno
import signal
import time

loop = asyncio.get_event_loop()

def quit():
	for bot in bots:
		asyncio.async(bot.disconnect())
	loop.stop()
for s in [signal.SIGTERM, signal.SIGINT]:
	loop.add_signal_handler(s, quit)

bots = []
for c in config.bots:
	if not c.autoconnect:
		continue
	bot = Bot(c)
	asyncio.async(bot.connect())
	bots.append(bot)
loop.run_forever()

'''
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
			cflags = flags.get(fd, 0)
			if cflags & select.EPOLLHUP == select.EPOLLHUP:
				bot.disconnect() # after a while, check_disconnect will return True
			elif cflags & select.EPOLLIN == select.EPOLLIN:
				bot.handle()
			elif bot.check_disconnect(ts):
				del fds[fd]
				epoll.unregister(fd)
				fd = bot.connect()
				fds[fd] = bot
				epoll.register(fd, EPOLLFLAGS)
		#commands.whelp(fds.values())
		log.flush()
	for b in fds.values():
		b.disconnect()
finally:
	epoll.close()
	log.close()
'''
