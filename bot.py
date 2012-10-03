from connection import Connection

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
		if len(split) > 2:
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
		}

		self.conn = Connection()
		self.conn.connect(config.host, config.port, config.nick, config.user)

	def handle(self):
		for line in self.conn.recv():
			msg = ServerMessage(line)
			handler = self.handlers.get(msg.command)
			if handler:
				handler(msg)

	def join(self, *channels):
		self.conn.send('JOIN', *channels)

	def say(self, target, message):
		self.conn.send('PRIVMSG', target, ':'+message)

	def __join_channels(self):
		if self.config.channels:
			self.join(*self.config.channels)

	def handle_ping(self, msg):
		self.conn.send('PONG', msg.target)

	def handle_motd(self, msg):
		self.registered = True
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
				self.__join_channels()
