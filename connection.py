import errno
import socket

socket.setdefaulttimeout(10)

class Connection:
	def __init__(self):
		self.socket = None
		self.last_buf = None
		self.debug = False

	def send(self, *data):
		line = ' '.join(data) + '\r\n'
		if self.debug: print('->', line, end='')
		self.socket.sendall(bytes(line, 'utf-8'))

	def recv(self):
		try:
			data = self.socket.recv(4096)
		except socket.error as e:
			if e.errno is None: # recv timed out
				return
			raise
		if self.last_buf is not None:
			data = self.last_buf + data
			self.last_buf = None
		lines = data.split(b'\r\n')
		for i in range(len(lines) - 1):
			line = str(lines[i], 'utf-8', 'replace')
			if self.debug: print('<-', line)
			yield line
		last = lines[-1]
		if last:
			self.last_buf = last

	def connect(self, host, port):
		if socket.has_ipv6:
			self.socket = socket.socket(socket.AF_INET6)
		else:
			self.socket = socket.socket(socket.AF_INET)
		error = self.__connect(host, port)
		if socket.has_ipv6 and (error == errno.ENETUNREACH or isinstance(error, socket.gaierror)):
			# tried ipv6 but we have no ipv6 connectivity or hostname doesn't have AAAA record
			self.socket.close()
			self.socket = socket.socket(socket.AF_INET)
			error = self.__connect(host, port)
		return error

	def __connect(self, host, port):
		try:
			error = self.socket.connect_ex((host, port))
		except socket.error as e:
			error = e
		return error

	def disconnect(self):
		if self.socket is None:
			return
		try:
			self.send('QUIT')
		except socket.error:
			pass
		self.socket.close()
		self.socket = None
