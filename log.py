from datetime import datetime

logfile = open('pbot.log', 'a')

def write(text):
	line = '%s %s' % (datetime.now(), text)
	if 0 <= line.rfind('\n') < len(line)-1:
		line += '\n\n'
	else:
		line += '\n'
	print(line, end='')
	logfile.write(line)

def close():
	global logfile
	logfile.close()
