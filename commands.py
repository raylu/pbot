from math import sqrt
import operator
import os
import re
import shlex
import signal
import subprocess
import time
import urllib

import psycopg2
import requests

import config
import log

rs = requests.Session()
rs.headers.update({'User-Agent': 'pbot'})
db = psycopg2.connect(config.settings['eve_dsn'])

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

		all_orders = xml.getElementsByTagName('all')[0]
		all_volume = all_orders.getElementsByTagName('volume')[0]
		volume = int(all_volume.childNodes[0].data)

		return bid, ask, volume
	def __item_info(curs, query):
		curs.execute(
				'SELECT "typeID", "typeName" FROM "invTypes" WHERE LOWER("typeName") LIKE %s',
				(query.lower(),))
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
					'SELECT "typeID", "typeName" FROM "invTypes" WHERE LOWER("typeName") LIKE %s',
					(item_name.lower(),))
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
	def format_prices(prices):
		if prices is None:
			return 'n/a'
		if prices[1] < 1000.0:
			return 'bid {0:g} ask {1:g} vol {2:,d}'.format(*prices)
		prices = map(int, prices)
		return 'bid {0:,d} ask {1:,d} vol {2:,d}'.format(*prices)

	if text.lower() == 'plex':
		text = "30 Day Pilot's License Extension (PLEX)"
	result = item_info(text)
	if not result:
		return
	typeid, item_name = result
	jita_system = 30000142
	amarr_system = 30002187
	jita_prices = get_prices(typeid, system=jita_system)
	amarr_prices = get_prices(typeid, system=amarr_system)
	jita = format_prices(jita_prices)
	amarr = format_prices(amarr_prices)
	bot.say(target, '%s - Jita: %s ; Amarr: %s' % (item_name, jita, amarr))

def jumps(bot, target, nick, command, text):
	split = text.split()
	if len(split) != 2:
		bot.say('usage: %s [from] [to]' % command)
		return
	with db.cursor() as curs:
		curs.execute('''
				SELECT "solarSystemName" FROM "mapSolarSystems"
				WHERE LOWER("solarSystemName") LIKE %s OR LOWER("solarSystemName") LIKE %s
				''', (split[0].lower() + '%', split[1].lower() + '%')
		)
		results = list(map(operator.itemgetter(0), curs.fetchmany(2)))
	query = [None, None]
	for i, s in enumerate(split):
		s = s.lower()
		for r in results:
			if r.lower().startswith(s):
				query[i] = r
				break
		else:
			bot.say(target, '%s: could not find system starting with %s' % (nick, s))
			break
	if None in query:
		return
	r = rs.get('http://api.eve-central.com/api/route/from/%s/to/%s' % (query[0], query[1]))
	try:
		jumps = r.json()
	except ValueError:
		bot.say(target, '%s: error getting jumps' % nick)
		return
	jumps_split = []
	for j in jumps:
		j_str = j['to']['name']
		from_sec = j['from']['security']
		to_sec = j['to']['security']
		if from_sec != to_sec:
			j_str += ' (%0.1g)' % to_sec
		jumps_split.append(j_str)
	bot.say(target, '%d jumps: %s' % (len(jumps), ', '.join(jumps_split)))

def calc(bot, target, nick, command, text):
	response = rs.get('https://www.calcatraz.com/calculator/api', params={'c': text})
	bot.say(target, '%s: %s' % (nick, response.text.rstrip()))

def roll(bot, target, nick, command, text):
	if not text:
		text = '1d6'
	response = rs.get('https://rolz.org/api/?' + urllib.parse.quote_plus(text))
	split = response.text.split('\n')
	details = split[2].split('=', 1)[1].strip()
	details = details.replace(' +', ' + ').replace(' +  ', ' + ')
	result = split[1].split('=', 1)[1]
	bot.say(target, "%s: %s = %s" % (nick, details, result))

def lightyears(bot, target, nick, command, text):
	split = [n + '%' for n in text.lower().split()]
	if len(split) != 2:
		bot.say(target, '%s: !%s [from] [to]' % (nick, command))
		return

	with db.cursor() as curs:
		curs.execute('''
				SELECT "solarSystemName", x, y, z FROM "mapSolarSystems"
				WHERE LOWER("solarSystemName") LIKE %s OR LOWER("solarSystemName") LIKE %s
				''', split)
		result = curs.fetchmany(6)
	if len(result) < 2:
		bot.say(target, nick + ': one or both systems not found')
		return
	elif len(result) > 2:
		bot.say(target, nick + ': found too many systems: ' + ' '.join(map(operator.itemgetter(0), result)))
		return

	dist = 0
	for d1, d2 in zip(result[0][1:], result[1][1:]):
		dist += (d1 - d2)**2
	dist = sqrt(dist) / 9.4605284e15 # meters to lightyears
	ship_ranges = [
		('CAP:', 2.5), # jump range for all other ships
		('BO:', 4.0), # blackops
		('JF:', 5.0), # jump freighters
	]
	jdc = []
	for ship, jump_range in ship_ranges:
		for level in range(0, 6):
			if dist <= jump_range * (1 + level * 0.2):
				jdc.append('%s %d' % (ship, level))
				break
		else:
			jdc.append(ship + ' N/A')
	bot.say(target, '%s ↔ %s: %.3f ly, %s' % (result[0][0], result[1][0], dist, ' '.join(jdc)))

def nodejs(bot, target, nick, command, text):
	cmd = ['../nsjail/nsjail', '-Mo', '--rlimit_as', '700', '--chroot', 'chroot',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo', '--',
			'/usr/bin/nodejs', '--print', text]
	proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, universal_newlines=True)
	stdout, stderr = proc.communicate()
	if proc.returncode == 0:
		output = stdout.split('\n', 1)[0]
	elif proc.returncode == 109:
		output = 'timed out after 2 seconds'
	else:
		try:
			output = stderr.split('\n', 5)[4]
		except IndexError:
			output = 'unknown error'
	bot.say(target, '%s: %s' % (nick, output[:250]))

def irb(bot, target, nick, command, text):
	cmd = ['../nsjail/nsjail', '-Mo', '--chroot', '',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo', '--',
			'/usr/bin/irb', '-f', '--noprompt']
	proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
	stdout, _ = proc.communicate(text)
	if proc.returncode == 109:
		output = 'timed out after 2 seconds'
	else:
		try:
			output = stdout.split('\n', 2)[2].lstrip('\n')
			output = output.split('\n', 1)[0][:250]
		except IndexError:
			output = 'unknown error'
	bot.say(target, '%s: %s' % (nick, output))

def python2(bot, target, nick, command, text):
	cmd = ['../nsjail/nsjail', '-Mo', '--chroot', 'chroot', '-E', 'LANG=en_US.UTF-8',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo', '--',
			'/usr/bin/python2', '-ESsi']
	proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, universal_newlines=True)
	stdout, stderr = proc.communicate(text + '\n')
	if proc.returncode == 0:
		stderr = stderr.split('\n', 2)[2] # ignore first 2 lines (version and compiler; python3 has -q for this)
		if stderr not in ['>>> >>> \n', '>>> ... \n>>> \n']:
			try:
				output = stderr.split('\n')[-3]
			except IndexError:
				output = ''
		else:
			output = stdout.split('\n', 1)[0]
	elif proc.returncode == 109:
		output = 'timed out after 2 seconds'
	else:
		output = 'unknown error'
	bot.say(target, '%s: %s' % (nick, output))

def python3(bot, target, nick, command, text):
	cmd = ['../nsjail/nsjail', '-Mo', '--chroot', 'chroot', '-E', 'LANG=en_US.UTF-8',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo', '--',
			'/usr/bin/python3', '-ISqi']
	proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, universal_newlines=True)
	stdout, stderr = proc.communicate(text + '\n')
	if proc.returncode == 0:
		if stderr not in ['>>> >>> \n', '>>> ... \n>>> \n']:
			try:
				output = stderr.split('\n')[-3]
			except IndexError:
				output = ''
		else:
			output = stdout.split('\n', 1)[0]
	elif proc.returncode == 109:
		output = 'timed out after 2 seconds'
	else:
		output = 'unknown error'
	bot.say(target, '%s: %s' % (nick, output))

def unicode_search(bot, target, nick, command, text):
	cmd = ['unicode', '--format', '{pchar} U+{ordc:04X} {name} (UTF-8: {utf8})\\n', '--max', '5', '--color', '0', text]
	output = subprocess.check_output(cmd)
	split = output.decode('utf-8').split('\n')
	if len(split) > 8: # text is something like '0000..ffff'
		return
	elif len(split) == 1:
		bot.say(target, '%s: nothing found' % nick)
	elif split[-2].startswith('Too many characters to display,'):
		split[-2] = split[-2][:split[-2].rfind(',')]
	bot.say(target, '    '.join(split))

def ddate(bot, target, nick, command, text):
	output = subprocess.check_output([command] + shlex.split(text), universal_newlines=True)
	bot.say(target, output.replace('\n', '    '))

handlers = {
	'pc': price_check,
	'jumps': jumps,
	'reload': reload,
	'calc': calc,
	'roll': roll,
	'ly': lightyears,
	'js': nodejs,
	'ruby': irb,
	'py2': python2,
	'py3': python3,
	'unicode': unicode_search,
	'ddate': ddate,
}

youtube_re = re.compile(r'((youtube\.com\/watch\?\S*v=)|(youtu\.be/))([a-zA-Z0-9-_]+)')
def youtube(bot, msg):
	match = youtube_re.search(msg.text)
	if match is None:
		return
	vid = match.group(4)
	params = {
		'id': vid,
		'part': 'contentDetails,snippet',
		'key': 'AIzaSyAehOw6OjS2ofPSSo9AerCGuBzStsX5tks',
	}
	response = rs.get('https://www.googleapis.com/youtube/v3/videos', params=params)
	if response.status_code == 400:
		bot.say(msg.target, "%s: invalid id" % msg.nick)
		return
	video = response.json()['items'][0]
	title = video['snippet']['title']
	duration = video['contentDetails']['duration']
	duration = duration[2:].replace('H', 'h ').replace('M', 'm ').replace('S', 's')
	date = video['snippet']['publishedAt'].split('T', 1)[0]
	bot.say(msg.target, "%s's video: %s, %s, %s" % (msg.nick, title, duration, date))

#last_kill_id = rs.get('http://api.whelp.gg/last').json()['kill_id']
#last_whelp_time = time.time()
def whelp(bots):
	from bot import STATE
	import traceback
	global last_kill_id, last_whelp_time

	if time.time() < last_whelp_time + 60:
		return
	try:
		kills = rs.get('http://api.whelp.gg/last/' + str(last_kill_id)).json()
		notify = []
		for k in kills:
			try:
				item_hull_ratio = (k['total_cost'] - k['hull_cost']) // k['hull_cost']
			except ZeroDivisionError:
				item_hull_ratio = 0
			# total > 30 billion or (total > 500 million and ratio > 7)
			if k['total_cost'] > 30e9 * 100 or (k['total_cost'] > 500e6 * 100 and item_hull_ratio > 7):
				notify.append(k)
			if k['kill_id'] > last_kill_id:
				last_kill_id = k['kill_id']

		for b in bots:
			if b.state == STATE.IDENTIFIED and '#ellipsis' in b.config.channels:
				for k in notify:
					cost = '{:,d}'.format(k['total_cost'] // 100 // int(1e6))
					line = '%s million ISK %s    http://www.whelp.gg/kill/%d' % (cost, k['ship_name'], k['kill_id'])
					b.say('#ellipsis', line)
		last_whelp_time = time.time()
	except:
		log.write(traceback.format_exc())
