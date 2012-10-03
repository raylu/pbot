from connection import Connection

class Bot:
	def __init__(self, config):
		self.config = config
		self.conn = Connection()
		self.conn.connect(config.host, config.port, config.nick, config.user)

	def handle(self):
		for line in self.conn.recv():
			if line[0] != ':':
				continue

			split = line[1:].split(' ', 3)
			source = split[0]
			command = split[1]
			target = split[2]

			nick = None
			exclaim = source.find('!')
			if exclaim != -1:
				nick = source[:exclaim]

			if command == 'NOTICE':
				assert split[3][0] == ':'
				message = split[3][1:]
				self.on_notice(nick, message)
			else:
				print('   ', line)

	def join(self, *channels):
		self.conn.send('JOIN', *channels)

	def on_notice(self, nick, message):
		print('notice: %s> %s' % (nick, message))
