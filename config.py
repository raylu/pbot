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

__doc = yaml.load(open('config.yaml', 'r'))
bots = (BotConfig(c) for c in __doc['bots'])
