from math import sqrt
import operator
import os
from os import path
import re
import shlex
import signal
import subprocess
import time
import urllib
import urllib.parse
import requests

import config
import log


rs = requests.Session()
rs.headers.update({'User-Agent': 'pbot'})


def reload(bot, target, nick, command, text):
	import sys
	import imp
	if config.settings['owner'] == nick:
		if config.settings['autoreload']:
			bot.notice(nick, 'not reloading: autoreload is on')
			return
		imp.reload(sys.modules[__name__])
		bot.notice(nick, 'reloaded!')

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

def nodejs(bot, target, nick, command, text):
	cmd = ['../nsjail/nsjail', '-Mo', '--rlimit_as', '700', '--chroot', chroot_dir,
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo',
			'--cgroup_mem_max', str(50 * MB), '--cgroup_pids_max', '1', '--quiet', '--',
			'/usr/bin/nodejs', '--print', text]
	proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, universal_newlines=True)
	stdout, stderr = proc.communicate()
	# https://github.com/nodejs/node/blob/master/doc/api/process.md#exit-codes is all lies
	if proc.returncode == 0:
		output = stdout.split('\n', 1)[0]
	elif proc.returncode == 109:
		output = 'timed out' # node catches OOM and exits 111; see below
	else:
		split = stderr.split('\n', 5)
		try:
			output = split[4]
		except IndexError:
			if split[0].startswith('FATAL ERROR:'):
				# often returncode 111 when OOM
				# curiously, the doc linked above claims a fatal error will exit 5
				# ENOMEM is 12. 128 - 5 - 12 = 111
				output = split[0]
			else:
				output = 'unknown error'
	bot.say(target, '%s: %s' % (nick, output[:250]))

def irb(bot, target, nick, command, text):
	cmd = ['../nsjail/nsjail', '-Mo', '--chroot', '',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo',
			'--cgroup_mem_max', str(50 * MB), '--cgroup_pids_max', '1', '--quiet', '--',
			'/usr/bin/irb', '-f', '--noprompt']
	proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
	stdout, _ = proc.communicate(text)
	if proc.returncode == 109:
		output = 'timed out or memory limit exceeded'
	else:
		try:
			output = stdout.split('\n', 2)[2].lstrip('\n')
			output = output.split('\n', 1)[0][:250]
		except IndexError:
			output = 'unknown error'
	bot.say(target, '%s: %s' % (nick, output))

def python2(bot, target, nick, command, text):
	cmd = ['../nsjail/nsjail', '-Mo', '--chroot', chroot_dir, '-E', 'LANG=en_US.UTF-8',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo',
			'--cgroup_mem_max', str(50 * MB), '--cgroup_pids_max', '1', '--quiet', '--',
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
		output = 'timed out or memory limit exceeded'
	else:
		output = 'unknown error'
	bot.say(target, '%s: %s' % (nick, output[:250]))

def python3(bot, target, nick, command, text):
	cmd = ['../nsjail/nsjail', '-Mo', '--chroot', chroot_dir, '-E', 'LANG=en_US.UTF-8',
			'-R/usr', '-R/lib', '-R/lib64', '--user', 'nobody', '--group', 'nogroup',
			'--time_limit', '2', '--disable_proc', '--iface_no_lo',
			'--cgroup_mem_max', str(50 * MB), '--cgroup_pids_max', '1', '--quiet', '--',
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
		output = 'timed out or memory limit exceeded'
	else:
		output = 'unknown error'
	bot.say(target, '%s: %s' % (nick, output[:250]))

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
	output = subprocess.check_output(['ddate'] + shlex.split(text), universal_newlines=True)
	bot.say(target, output.replace('\n', '    '))

def units(bot, target, nick, command, text):
	command = ['units', '--compact', '--one-line', '--quiet'] + text.split(' in ', 1)
	proc = subprocess.Popen(command, stdout=subprocess.PIPE, universal_newlines=True)
	output, _ = proc.communicate()
	bot.say(target, output.replace('\n', '  ')[:250])



youtube_re = re.compile(r'((youtube\.com\/watch\?\S*v=)|(youtu\.be/))([a-zA-Z0-9-_]+)')
def youtube(bot, msg):
	match = youtube_re.search(msg.text)
	if match is None:
		return
	vid = match.group(4)
	params = {
		'id': vid,
		'part': 'contentDetails,snippet',
		'key': config.settings['youtube_key'],
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

def weather(bot, target, nick, command, text):
	url = 'https://api.wunderground.com/api/%s/conditions/q/%s.json' % (
			config.settings['weather_key'], urllib.parse.quote_plus(text.replace(' ', '_')))
	response = rs.get(url)
	response.raise_for_status()
	data = response.json()
	if 'current_observation' in data:
		current = data['current_observation']
		output = '%s: %s, feels like %s. %s\n%s' % (
				current['display_location']['full'], current['temperature_string'], current['feelslike_string'],
				current['weather'], current['forecast_url'])
		bot.say(target, output)
	elif 'results' in data['response']:
		bot.say(target, '%s: got %s results. try narrowing your search' % (
				nick, len(data['response']['results'])))
	else:
		bot.say(target, '%s: error fetching results' % nick)

handlers = {
	'reload': reload,

	'calc': calc,
	'roll': roll,

	'js': nodejs,
	'ruby': irb,
	'py2': python2,
	'py3': python3,

	'unicode': unicode_search,
	'ddate': ddate,
	'units': units,
	'weather': weather,
	'w': weather
}
