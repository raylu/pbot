# https://github.com/thatch45/sandbox/blob/master/examples/daemonize/python3.py

import os
import sys

def daemonize():
	pid = os.fork()
	if pid > 0:
		sys.exit(0)

	os.setsid()
	os.umask(0o22)

	pid = os.fork()
	if pid > 0:
		print('backgrounding, pid: %d' % pid)
		sys.exit(0)

	dev_null = open('/dev/null', 'w')
	os.dup2(dev_null.fileno(), sys.stdin.fileno())
	os.dup2(dev_null.fileno(), sys.stdout.fileno())
	os.dup2(dev_null.fileno(), sys.stderr.fileno())
