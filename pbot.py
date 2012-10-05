#!/usr/bin/env python3

import config
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

while True:
	results = epoll.poll()
	for fd, flags in results:
		bot = fds[fd]
		bot.handle()
