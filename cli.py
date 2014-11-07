from snapchat import Snapchat
from datetime import datetime
import os
import sys
import subprocess
import getpass
import re

PATH = './snaps/'
EXTENSIONS = ['jpeg', 'jpg', 'mp4']

def cli():
	clear()
	s = Snapchat()
	username = raw_input('Please enter username: ')
	password = getpass.getpass('Please enter password: ')

	if not s.login(username, password):
		print 'Invalid username/password combo'
		clear()
		exit()

	snaps = s.get_snaps()
	user_input = None
	functions = {
		'R': lambda: s.get_snaps(),
		'S': send
	}
	clear()
	while user_input != 'X':
		print 'Welcome to Snapchat!'
		print
		print '{0} pending snaps:'.format(len(snaps))
		num = 1
		for snap in snaps:
			dt = datetime.fromtimestamp(snap['sent']/1000)
			ext = s.media_type(snap['media_type'], binary=False)
			timestamp = str(snap['sent']).replace(':', '-')
			filename = '{}+{}+{}.{}'.format(timestamp, snap['sender'], snap['id'], ext)
			path = PATH + filename

			# check if file already exists so we don't need to redownload
			if not os.path.isfile(path):
				data = s.get_snap(snap['id'])
				with open(path, 'wb') as outfile:
					outfile.write(data)

			snap['path'] = path
			print '[{0}] Snap from {1} (Sent {2})'.format(num, snap['sender'], dt)
			num += 1
		print
		print '[R] - refresh snaps'
		print '[S] - send a snap'
		print '[X] - exit'
		user_input = raw_input('Enter an option: ').upper()
		num_input = int(user_input) if user_input.isdigit() else None
		if num_input <= len(snaps) and num_input > 0:
			file_path = snaps[num_input-1]['path']

			# open /dev/null or equivalent so we can redirect stdout/stderr to it 
			nullfile = open(os.devnull, 'w')

			# cross-platform method to open a media file
			if sys.platform.startswith('linux'):
				subprocess.Popen(['xdg-open', file_path], stdout=nullfile, stderr=nullfile) 
			elif sys.platform.startswith('darwin'):
				subprocess.Popen(['open', file_path], stdout=nullfile, stderr=nullfile)
			elif sys.platform.startswith('win'):
				subprocess.Popen(['start', file_path], stdout=nullfile, stderr=nullfile)
			else:
				print 'I don\'t recognize your operating system: {0}'.format(sys.platform)
		elif user_input in functions:
			if user_input == 'R':
				snaps = functions[user_input]()
				print 'Refreshed!'
			else:
				functions[user_input](s)
		elif user_input != 'X':
			print 'I don\'t recognize that command.'

		if user_input != 'X':
			raw_input('Press enter to continue...')
			clear()

def send(s):
	secondary_input = raw_input('Enter path to file: ')
	path = secondary_input

	# check that the file path is valid
	if not os.path.isfile(path):
		print 'That is not a valid file'
		return

	# check that the file is a valid type
	file_extension = os.path.splitext(path)[1]
	if file_extension.lower().replace('.', '') not in EXTENSIONS:
		print 'Not a compatible file'
		return

	secondary_input = raw_input('Enter comma-separated list of recipient usernames: ')
	try:
		recipients = secondary_input.lower().split(',')
		if s.send_snap(path, recipients):
			print 'Sent {0} to {1}'.format(path, recipients)
		else:
			print 'Error sending snap'
	except:
		print 'Exception thrown while sending snap'

# clears the terminal and resets scroll position to top left
# using ANSI escape characters
def clear():
	print chr(27) + "[2J" + chr(27) + "[H"

if __name__ == '__main__':
	cli()
