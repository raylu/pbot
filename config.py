import yaml

class BotConfig:
	attrs = frozenset([
		'host',
		'port',
		'nick',
		'user',
		'nickserv',
		'channels',
		'autoconnect',
	])

	def __init__(self, cdict):
		attrs = set(self.attrs) # copy and "unfreeze"
		for k, v in cdict.items():
			attrs.remove(k) # check if the key is allowed, mark it as present
			setattr(self, k, v)
		if len(attrs) != 0:
			raise KeyError('missing required bot config keys: %s' % attrs)

	def __str__(self):
		return '<BotConfig: %s>' % self.__dict__

__doc = yaml.load(open('config.yaml', 'r'))
bots = (BotConfig(c) for c in __doc['bots'])
settings = __doc['settings']

# the maximum amount of time to detect a disconnection:
# 0s: we epoll, handle data, and epoll again
# 1s: someone pulls the plug
# 30s: epoll times out, we check_disconnect, and epoll again
# 60s: same as 30s
# 89s: epoll returns for some other bot; we check_disconnect and epoll again
# 119s: epoll times out, we check_disconnect and send a ping (119 > 90), then epoll
# 149s: epoll times out, we check_disconnect, then epoll
# 179s: epoll times out, we check_disconnect and decide we're disconnected (179 > 90 + 60)
EPOLL_TIMEOUT = 30
PING_INTERVAL = 90 # if no data is received for this many seconds, send the server a PING
PING_TIMEOUT = 60
