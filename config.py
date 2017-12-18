import yaml

class BotConfig:
	attrs = frozenset([
		'host',
		'port',
		'use_ssl',
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

with open('config.yaml', 'r') as f:
	__doc = yaml.load(f)
bots = (BotConfig(c) for c in __doc['bots'])
settings = __doc['settings']

PING_INTERVAL = 90 # if no data is received for this many seconds, send the server a PING
PING_TIMEOUT = 60
