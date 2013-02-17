import config

import re

import requests
import oursql

rs = requests.session(headers={'User-Agent': 'pbot'})
db = oursql.connect(db='eve', user='eve', passwd='eve', autoreconnect=True)

def reload(bot, target, nick, command, text):
	import sys
	import imp
	if config.settings['owner'] == nick:
		if config.settings['autoreload']:
			bot.notice(nick, 'not reloading: autoreload is on')
			return
		imp.reload(sys.modules[__name__])
		bot.notice(nick, 'reloaded!')

def price_check(bot, target, nick, command, text):
	def get_prices(typeid, system=None, region=None):
		from xml.dom import minidom
		import xml.parsers.expat

		url = 'http://api.eve-central.com/api/marketstat'
		params = {'typeid': typeid}
		if system: params['usesystem'] = system
		if region: params['regionlimit'] = region
		try:
			xml = minidom.parseString(rs.get(url, params=params).text)
		except xml.parsers.expat.ExpatError:
			return None

		buy = xml.getElementsByTagName('buy')[0]
		buy_max = buy.getElementsByTagName('max')[0]
		bid = float(buy_max.childNodes[0].data)

		sell = xml.getElementsByTagName('sell')[0]
		sell_min = sell.getElementsByTagName('min')[0]
		ask = float(sell_min.childNodes[0].data)

		return bid, ask
	def __item_info(curs, query):
		curs.execute(
				'SELECT typeID, typeName FROM invTypes WHERE typeName LIKE ?',
				(query,)
				)
		results = curs.fetchmany(3)
		if len(results) == 1:
			return results[0]
		if len(results) == 2 and \
				results[0][1].endswith('Blueprint') ^ results[1][1].endswith('Blueprint'):
			# an item and its blueprint; show the item
			if results[0][1].endswith('Blueprint'):
				return results[1]
			else:
				return results[0]
		if len(results) >= 2:
			return results
	def item_info(item_name):
		with db.cursor() as curs:
			# exact match
			curs.execute(
					'SELECT typeID, typeName FROM invTypes WHERE typeName LIKE ?',
					(item_name,)
					)
			result = curs.fetchone()
			if result:
				return result

			# start of string match
			results = __item_info(curs, item_name + '%')
			if isinstance(results, tuple):
				return results
			if results:
				names = map(lambda r: r[1], results)
				bot.say(target, 'Found items: ' + ', '.join(names))
				return

			# substring match
			results = __item_info(curs, '%' + item_name + '%')
			if isinstance(results, tuple):
				return results
			if results:
				names = map(lambda r: r[1], results)
				bot.say(target, 'Found items: ' + ', '.join(names))
				return
			bot.say(target, 'Item not found')

	if text.lower() == 'plex':
		text = "30 Day Pilot's License Extension (PLEX)"
	result = item_info(text)
	if not result:
		return
	typeid, item_name = result
	jita_system = 30000142
	jita_prices = get_prices(typeid, system=jita_system)
	jita = 'n/a'
	if jita_prices is not None:
		jita = 'bid {:,d} ask {:,d}'.format(int(jita_prices[0]), int(jita_prices[1]))
	bot.say(target, '%s - Jita: %s' % (item_name, jita))

entity_re = re.compile(r'&(#?)(x?)(\w+);')
def calc(bot, target, nick, command, text):
	import codecs
	import html.entities
	def substitute_entity(match):
		ent = match.group(3)
		if match.group(1) == "#":
			if match.group(2) == '':
				return chr(int(ent))
			elif match.group(2) == 'x':
				return chr(int('0x'+ent, 16))
		else:
			cp = html.entities.name2codepoint.get(ent)
			if cp:
				return chr(cp)
			return match.group()
	def decode_htmlentities(string):
		return entity_re.subn(substitute_entity, string)[0]

	if not text:
		return
	response = rs.get('http://www.google.com/ig/calculator', params={'hl': 'en', 'q': text}).text
	match = re.match('{lhs: "(.*)",rhs: "(.*)",error: "(.*)",icc: (true|false)}', response)
	if match is None or match.group(3) != '':
		bot.say(target, nick + ': Error calculating.')
		return
	output = "%s = %s" % (match.group(1), match.group(2))
	output = codecs.getdecoder('unicode_escape')(output)[0]
	output = re.subn('<sup>(.*)</sup>', r'^(\1)', output)[0]
	output = decode_htmlentities(output)
	bot.say(target, '%s: %s' % (nick, output))

handlers = {
	'pc': price_check,
	'reload': reload,
	'calc': calc,
}

youtube_re = re.compile('((youtube\.com\/watch\?v=)|(youtu\.be/))([a-zA-Z0-9-_]+)')
def youtube(bot, msg):
	match = youtube_re.search(msg.text)
	if match is None:
		return
	vid = match.group(4)
	url = 'http://gdata.youtube.com/feeds/api/videos/' + vid
	params = {
		'v': 2,
		'strict': True,
		'alt': 'json',
	}
	response = rs.get(url, params=params).json
	if response is None:
		return
	entry = response['entry']
	title = entry['title']['$t']
	seconds = int(entry['media$group']['yt$duration']['seconds'])
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)
	duration = '%02d:%02d' % (minutes, seconds)
	if hours > 0:
		duration = '%s:%s' % (hours, duration)
	bot.say(msg.target, "%s's video: %s, %s" % (msg.nick, title, duration))
