#!/usr/bin/env python3

import sys
if sys.argv[-1] == '-d':
	from daemon import daemonize
	daemonize()

from bot import Bot
import config
import log

import signal
import threading
import time

def quit(signum, frame):
	for bot in bots:
		bot.disconnect()
	log.close()
	sys.exit()
for s in [signal.SIGTERM, signal.SIGINT]:
	signal.signal(s, quit)
	signal.siginterrupt(s, False)

bots = []
for c in config.bots:
	if not c.autoconnect:
		continue
	bot = Bot(c)
	bots.append(bot)
	threading.Thread(target=bot.connect, daemon=True).start()

while True:
	time.sleep(600)
