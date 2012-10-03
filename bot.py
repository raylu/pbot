from connection import Connection

class NickservStates:
	UNIDENTIFIED = 0
	IDENTIFYING = 1
	IDENTIFIED = 2
NICKSERV = NickservStates()

class Bot:

	def __init__(self, config):
		self.config = config
		self.conn = Connection()
		self.conn.connect(config.host, config.port, config.nick, config.user)
		self.nickserv_state = NICKSERV.UNIDENTIFIED
		self.registered = False # has the server accepted our host/nick/user?

	def handle(self):
		for line in self.conn.recv():
			nick = None
			if line[0] == ':':
				split = line[1:].split(' ', 3)
				source = split.pop(0)
				exclaim = source.find('!')
				if exclaim != -1:
					nick = source[:exclaim]
			else:
				split = line.split(' ', 2)

			command = split[0]
			target = split[1]
			message = None
			if len(split) > 2:
				message = split[2]
				if message[0] == ':':
					message = message[1:]

			if command == 'PING':
				self.on_ping(target)
			elif command == '376': # RPL_ENDOFMOTD
				self.registered = True
				if self.config.nickserv is None:
					self.nickserv_state = NICKSERV.IDENTIFIED
					self.__join_channels()
			elif command == 'NOTICE':
				self.on_notice(nick, message)
			elif command == 'MODE':
				self.on_mode(nick, target, message)

	def join(self, *channels):
		self.conn.send('JOIN', *channels)

	def msg(self, target, message):
		self.conn.send('PRIVMSG', target, ':'+message)

	def __join_channels(self):
		if self.config.channels:
			self.join(*self.config.channels)

	def on_ping(self, cookie):
		self.conn.send('PONG', cookie)

	def on_notice(self, nick, message):
		if not self.registered: # AUTH :*** Looking up your hostname...
			return

		if self.nickserv_state < NICKSERV.IDENTIFYING:
			if self.config.nickserv is None:
				self.nickserv_state = NICKSERV.IDENTIFIED
				self.__join_channels()
			elif nick.upper() == 'NICKSERV':
				self.msg(nick, 'IDENTIFY ' + self.config.nickserv)
				self.nickserv_state = NICKSERV.IDENTIFYING

	def on_mode(self, nick, target, message):
		if target == self.config.nick:
			if message == '+r':
				self.nickserv_state = NICKSERV.IDENTIFIED
				self.__join_channels()
