import socket

socket.setdefaulttimeout(180)

class Connection:
	def __init__(self):
		self.socket = None
		self.last_buf = None
		self.debug = False

	def send(self, *data):
		line = ' '.join(data) + '\r\n'
		if self.debug: print('->', line, end='')
		self.socket.send(bytes(line, 'utf-8'))

	def recv(self):
		data = str(self.socket.recv(4096), 'utf-8')
		if self.last_buf is not None:
			data = self.last_buf + data
			self.last_buf = None
		lines = data.split('\r\n')
		for i in range(len(lines) - 1):
			if self.debug: print('<-', lines[i])
			yield lines[i]
		last = lines[-1]
		if last:
			self.last_buf = last
			return

	def connect(self, host, port, nick, user):
		self.socket = socket.create_connection((host, port))
		self.send('NICK', nick)
		self.send('USER', user, 'pbot', 'pbot', ':'+user)
