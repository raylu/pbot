#!/usr/bin/env python3

from config import Config, get_configs
from bot import Bot

import select

epoll = select.epoll()
EPOLLFLAGS = select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP

configs = get_configs()
fds = {}
for c in configs:
	bot = Bot(c)
	fd = bot.conn.socket.fileno()
	fds[fd] = bot
	epoll.register(fd, EPOLLFLAGS)

while True:
	results = epoll.poll()
	for fd, flags in results:
		bot = fds[fd]
		bot.handle()
