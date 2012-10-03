import socket

socket.setdefaulttimeout(30)

class Connection:
	def __init__(self):
		self.socket = None

	def send(self, *data):
		line = ' '.join(data) + '\r\n'
		self.socket.send(bytes(line, 'utf-8'))
		self.last_buf = None

	def recv(self):
		data = str(self.socket.recv(4096), 'utf-8')
		if self.last_buf is not None:
			data = self.last_buf + data
			self.last_buf = None
		lines = data.split('\r\n')
		if not len(lines):
			self.last_buf = data
			return

		for i in range(len(lines) - 1):
			yield lines[i]
		last = lines[-1]
		if last[-2:] != '\r\n':
			self.last_buf = last
			return
		yield last

	def connect(self, host, port, nick, user):
		self.socket = socket.create_connection((host, port))
		self.send('NICK', nick)
		self.send('USER', user, 'pbot', 'pbot', ':'+user)
