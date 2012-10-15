from connection import Connection
import config
import log
import commands

import imp
import sys
import traceback
import os

os.stat_float_times(False)
commands_mtime = os.stat('commands.py').st_mtime

class NickservStates:
	UNIDENTIFIED = 0
	IDENTIFYING = 1
	IDENTIFIED = 2
NICKSERV = NickservStates()

class ServerMessage:
	''' nick, command, target, text '''
	def __init__(self, line):
		self.nick = None
		if line[0] == ':':
			split = line[1:].split(' ', 3)
			source = split.pop(0)
			exclaim = source.find('!')
			if exclaim != -1:
				self.nick = source[:exclaim]
		else:
			split = line.split(' ', 2)

		self.command = split[0]
		self.target = split[1]
		self.text = None
		if len(split) > 2 and split[2]:
			self.text = split[2]
			if self.text[0] == ':':
				self.text = self.text[1:]

		self.line = line

	def __str__(self):
		return 'ServerMessage(%r)' % self.line

class Bot:
	def __init__(self, config):
		self.config = config
		self.nickserv_state = NICKSERV.UNIDENTIFIED
		self.registered = False # has the server accepted our host/nick/user?

		self.handlers = {
			'PING': self.handle_ping,
			'376': self.handle_motd, # RPL_ENDOFMOTD
			'NOTICE': self.handle_notice,
			'MODE': self.handle_mode,
			'PRIVMSG': self.handle_privmsg,
		}

		log.write('connecting to %s:%d...' % (config.host, config.port))
		self.conn = Connection()
		self.conn.connect(config.host, config.port, config.nick, config.user)

	def __str__(self):
		return '<Bot: %s/%s>' % (config.host, config.nick)

	def exception(self, line):
		exc_type, exc_value, exc_tb = sys.exc_info()
		exc_list = traceback.format_exception(exc_type, exc_value, exc_tb)
		self.log(line + '\n' + ''.join(exc_list))

		path, lineno, method, code = traceback.extract_tb(exc_tb)[-1]
		path = os.path.relpath(path)
		exc_name = exc_type.__name__
		notice = '%s:%s():%d %s: %s' % (path, method, lineno, exc_name, exc_value)
		if code is not None:
			notice += ' | ' + code[:50]
		self.notice(config.settings['owner'], notice)


	def log(self, text):
		log.write('%s/%s: %s' % (self.config.host, self.config.nick, text))

	def handle(self):
		for line in self.conn.recv():
			msg = ServerMessage(line)
			handler = self.handlers.get(msg.command)
			if handler:
				try:
					handler(msg)
				except:
					self.exception(line)

	def join(self, *channels):
		self.conn.send('JOIN', *channels)

	def say(self, target, message):
		self.conn.send('PRIVMSG', target, ':'+message)

	def notice(self, target, message):
		self.conn.send('NOTICE', target, ':'+message)

	def disconnect(self):
		self.log('disconnecting')
		self.conn.disconnect()

	def __join_channels(self):
		self.log('autojoining channels...')
		if self.config.channels:
			self.join(*self.config.channels)

	def handle_ping(self, msg):
		self.conn.send('PONG', msg.target)

	def handle_motd(self, msg):
		self.registered = True
		self.log('server accepted host/nick/user')
		if self.config.nickserv is None:
			self.nickserv_state = NICKSERV.IDENTIFIED
			self.__join_channels()

	def handle_notice(self, msg):
		if not self.registered: # AUTH :*** Looking up your hostname...
			return

		if self.nickserv_state < NICKSERV.IDENTIFYING:
			if self.config.nickserv is None:
				self.nickserv_state = NICKSERV.IDENTIFIED
				self.__join_channels()
			elif msg.nick.upper() == 'NICKSERV':
				self.say(msg.nick, 'IDENTIFY ' + self.config.nickserv)
				self.nickserv_state = NICKSERV.IDENTIFYING

	def handle_mode(self, msg):
		if msg.target == self.config.nick:
			if msg.text == '+r':
				self.nickserv_state = NICKSERV.IDENTIFIED
				self.log('nickserv accepted identification')
				self.__join_channels()

	def handle_privmsg(self, msg):
		if msg.target != self.config.nick:
			if msg.text[0] == '!' and len(msg.text) > 1:
				split = msg.text[1:].split(' ', 1)
				command = split[0]
				text = ''
				if len(split) > 1:
					text = split[1]

				if config.settings['autoreload']:
					global commands_mtime
					new_mtime = os.stat('commands.py').st_mtime
					if new_mtime > commands_mtime:
						imp.reload(commands)
						commands_mtime = new_mtime
				handler = commands.handlers.get(command)
				if handler:
					handler(self, msg.target, msg.nick, command, text)
			else:
				commands.youtube(self, msg)
