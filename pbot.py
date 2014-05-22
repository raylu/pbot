#!/usr/bin/env python3

import config

import sys
if sys.argv[-1] == '-d':
	from daemon import daemonize
	daemonize()

import log
from bot import Bot
import commands

import asyncore
import errno
import select
import signal
import time

for c in config.bots:
	if not c.autoconnect:
		continue
	bot = Bot(c)
	bot.connect_irc()
asyncore.loop()
