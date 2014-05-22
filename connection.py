import asyncio
import socket

class Connection(asyncio.Protocol):
	def __init__(self):
		self.reader = self.writer = None
		self.last_buf = None
		self.debug = False

	def send(self, *data):
		line = ' '.join(data) + '\r\n'
		if self.debug: print('->', line, end='')
		self.writer.write(line.encode('utf-8'))

	@asyncio.coroutine
	def recv(self):
		data = yield from self.reader.read(4096)
		if self.last_buf is not None:
			data = self.last_buf + data
			self.last_buf = None
		raw_lines = data.split(b'\r\n')
		lines = []
		for raw_line in raw_lines[:-1]:
			line = raw_line.decode('utf-8', 'replace')
			if self.debug: print('<-', line)
			lines.append(line)
		last = raw_lines[-1]
		if last:
			self.last_buf = last
		return lines

	@asyncio.coroutine
	def connect(self, host, port):
		self.reader, self.writer = yield from asyncio.open_connection(host, port)

	@asyncio.coroutine
	def disconnect(self):
		if self.reader is None:
			return
		self.send('QUIT')
		yield from self.writer.drain()
		self.writer.write_eof()
		self.reader = self.writer = None
