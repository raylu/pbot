from datetime import datetime
import os
import sys

logfile = open('pbot.log', 'a')
stdout = os.isatty(sys.stdout.fileno())

def write(text):
	line = '%s %s' % (datetime.now(), text)
	if 0 <= line.rfind('\n') < len(line)-1:
		line += '\n\n'
	else:
		line += '\n'

	if stdout:
		print(line, end='')
	logfile.write(line)

def flush():
	logfile.flush()

def close():
	logfile.close()
