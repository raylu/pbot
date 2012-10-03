import yaml

class Config:
	attrs = frozenset(['host', 'port', 'nick', 'user', 'channels'])

	def __init__(self, cdict):
		attrs = set(self.attrs)
		for k, v in cdict.items():
			attrs.remove(k)
			setattr(self, k, v)
		if len(attrs) != 0:
			raise KeyError('missing required bot config keys: %s' % attrs)

def get_configs():
	doc = yaml.load(open('config.yaml', 'r'))
	configs = []
	for b in doc['bots']:
		yield Config(b)
