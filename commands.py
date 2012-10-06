import config

import requests
import oursql

rs = requests.session(headers={'User-Agent': 'pbot'})
db = oursql.connect(db='eve', user='eve', passwd='eve', autoping=True)

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

	curs = db.cursor()
	try:
		item_name = text
		curs.execute('''
			SELECT typeID, typeName
			FROM invTypes
			WHERE typeName LIKE ?;
		''', (item_name,))
		result = curs.fetchone()
		if result is None:
			bot.say(target, 'Item not found')
			return
		typeid = result[0]
		item_name = result[1]
	finally:
		curs.close()

	jita_system = 30000142
	detorid_region = 10000005
	jita_prices = get_prices(typeid, system=jita_system)
	detorid_prices = get_prices(typeid, region=detorid_region)
	jita = 'n/a'
	detorid = 'n/a'
	if jita_prices is not None:
		jita = 'bid {:,d} ask {:,d}'.format(int(jita_prices[0]), int(jita_prices[1]))
	if detorid_prices is not None:
		detorid = 'bid {:,d} ask {:,d}'.format(int(detorid_prices[0]), int(detorid_prices[1]))
	bot.say(target, '%s - Jita: %s ; Detorid: %s' % (item_name, jita, detorid))

handlers = {
	'pc': price_check,
	'reload': reload,
}
