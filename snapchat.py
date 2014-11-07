import requests
import hashlib
import json
import time
import uuid

from datetime import datetime
from Crypto.Cipher import AES

# Snapchat API wrapper class
# Code partially derived from the snapchat-python project (MIT License)
# https://github.com/niothiel/snapchat-python
class Snapchat:
	URL =					'https://feelinsonice-hrd.appspot.com/'
	SECRET =				'iEk21fuwZApXlz93750dmW22pw389dPwOk'
	STATIC_TOKEN =			'm198sOkJEn37DjqZ32lpRu76xmw288xSQ9'
	BLOB_ENCRYPTION_KEY =	'M02cnQ51Ji97vwT4'
	HASH_PATTERN =			'0001110111101110001111010101111011010001001110011000110001000110'
	SNAPCHAT_VERSION =		'7.1.0.10'
	USERAGENT =				'Snapchat/{0} (iPhone; iOS 8.1.1; gzip)'.format(SNAPCHAT_VERSION)

	MEDIA_IMAGE = 							0
	MEDIA_VIDEO =							1
	MEDIA_VIDEO_NOAUDIO =					2
	MEDIA_FRIEND_REQUEST =					3
	MEDIA_FRIEND_REQUEST_IMAGE =			4
	MEDIA_FRIEND_REQUEST_VIDEO =			5
	MEDIA_FRIEND_REQUEST_VIDEO_NOAUDIO =	6

	STATUS_NONE =						   -1
	STATUS_SENT =							0
	STATUS_DELIVERED =						1
	STATUS_OPENED = 						2
	STATUS_SCREENSHOT = 					3

	FRIEND_CONFIRMED =						0
	FRIEND_UNCONFIRMED =					1
	FRIEND_BLOCKED =						2
	FRIEND_DELETED =						3

	PRIVACY_EVERYONE =						0
	PRIVACY_FRIENDS =						1
	
	def __init__(self, username=None, password=None):
		self.username = username
		self.auth_token = None 
		self.logged_in = False 
		self.cipher = AES.new(Snapchat.BLOB_ENCRYPTION_KEY, AES.MODE_ECB)
		if username is not None and password is not None:
			self.login(username, password)

	# Snapchat uses some weird method to derive their authentication token
	def _pad(self, data, blocksize=16):
		pad = blocksize - (len(data) % blocksize)
		return data + chr(pad) * pad

	def _hash(self, first, second):
		first = Snapchat.SECRET + str(first)
		second = str(second) + Snapchat.SECRET
		hash1 = hashlib.sha256(first).hexdigest();
		hash2 = hashlib.sha256(second).hexdigest();
		result = ''
		for pos, included in enumerate(Snapchat.HASH_PATTERN):
			if included == '0':
				result += hash1[pos]
			else:
				result += hash2[pos]
		return result

	def _encrypt(self, data):
		data = self._pad(data)
		return self.cipher.encrypt(data)

	def _decrypt(self, data):
		data = self._pad(data)
		return self.cipher.decrypt(data)

	# convenience method to get a request_token
	def _tokenize(self, params):
		return self._hash(params[0], params[1])

	# get time in microseconds
	def _timestamp(self):
		return int(time.time() * 1000)

	# get the media type in human-readable format
	# set binary to True if passing in a data stream
	# set binary to False if passing in a media type (int) 
	def media_type(self, media, binary=True):
		if binary:
			if media[0] == chr(0xff) and media[1] == chr(0xd8):
				return 'jpg'

			if media[0] == chr(0x00) and media[1] == chr(0x00):
				return 'mp4'
		else:
			if media == Snapchat.MEDIA_IMAGE:
				return 'jpg'

			if media == Snapchat.MEDIA_VIDEO:
				return 'mp4'

		return None

	# get the integer representing the type of media of a file
	def media_type_num(self, media):
		if media[0] == chr(0xff) and media[1] == chr(0xd8):
			return Snapchat.MEDIA_IMAGE

		if media[0] == chr(0x00) and media[1] == chr(0x00):
			return Snapchat.MEDIA_VIDEO

		return -1
	
	# send a POST request to Snapchat's backend with the given data/params/file
	def api_post(self, endpoint, data, params, upload_file = None):
		data['req_token'] = self._tokenize(params);
		headers = {'User-Agent': Snapchat.USERAGENT}
		url = Snapchat.URL + endpoint

		# upload file in multipart request if necessary
		# verify is set to False for debugging purposes with Fiddler
		if upload_file is not None:
			r = requests.post(url, data, headers=headers, files={'data': upload_file}, verify=False)
		else:
			r = requests.post(url, data, headers=headers, verify=False)

		# check for HTTP 200 OK status, anything else means error
		if r.status_code != 200:
			print url
			print data
			print headers
			print r.content
			return None

		# attempt to parse response as JSON
		try:
			return json.loads(r.content)
		except:
			return r.content
		
	# send a GET request to Snapchat's backend with the given params
	def api_get(self, endpoint, params):
		url = Snapchat.URL + endpoint
		headers = {'User-Agent': Snapchat.USERAGENT}
		r = requests.get(url, params=params, headers=headers)

		# check for HTTP 200 OK status, anything else means error
		if r.status_code != 200:
			print url
			print data
			print headers
			print r.content
			return None

		# attempt to parse response as JSON
		try:
			return json.loads(r.content)
		except:
			return r.content

	# log into Snapchat with the given credentials
	def login(self, username, password):
		timestamp = self._timestamp()
		data = {
			'username': username,
			'password': password,
			'timestamp': timestamp
		}
		params = [
			Snapchat.STATIC_TOKEN,
			timestamp
		]
		result = self.api_post('loq/login', data, params)

		updates = result['updates_response']

		if 'auth_token' in updates:
			self.auth_token = updates['auth_token']
		if 'username' in updates:
			self.username = updates['username']
		if self.auth_token is not None and self.username is not None:
			self.logged_in = True
		else:
			return False

		return result

	# get all updates for this user (including snaps, stories,
	# chat messages, friend list, etc)
	def get_updates(self):
		if not self.logged_in:
			return False

		timestamp = self._timestamp()
		data = {
			'timestamp': timestamp,
			'username': self.username,
			'checksum': ''
		}
		params = [
			self.auth_token,
			timestamp
		]
		result = self.api_post('loq/all_updates', data, params)
		return result

	# send a snap with the given media type, recipients and view time
	def send_snap(self, filename, recipients, media_type=None, time=10):
		if not self.logged_in:
			return False 

		with open(filename, 'rb') as infile:
			decrypted_file = (infile.read())

		if media_type is None:
			media_type = self.media_type_num(decrypted_file)

		encrypted_file = self._encrypt(decrypted_file)

		timestamp = self._timestamp()
		media_id = self.username.upper() + '~' + str(uuid.uuid4()).upper()
		data = {
			'media_id': media_id,
			'type': media_type,
			'timestamp': timestamp,
			'username': self.username,
			'zipped': 0
		}
		params = [
			self.auth_token,
			timestamp
		]

		result = self.api_post('bq/upload', data, params, encrypted_file)

		if result is None:
			return False 

		if not isinstance(recipients, list):
			recipients = [recipients]

		timestamp = self._timestamp()
		data = {
			'recipients': '[' + ','.join(recipients) + ']',
			'media_id': media_id,
			'time': time,
			'reply': 0,
			'country_code': 'US',
			'timestamp': timestamp,
			'username': self.username,
			'zipped': 0
		}
		params = [
			self.auth_token,
			timestamp
		]

		result = self.api_post('loq/send', data, params)
		return result['snap_response']['success'] 

	# retrieve a snap from Snapchat with the given ID
	def get_snap(self, snap_id):
		if not self.logged_in:
			return False

		timestamp = self._timestamp()
		data = {
			'id': snap_id,
			'timestamp': timestamp,
			'username': self.username}

		params = [self.auth_token, timestamp]
		result = self.api_post('bq/blob', data, params)

		if result is None:
			return False

		# if it's decrypted already, just return
		if self.media_type(result) is not None:
			return result

		result = self._decrypt(result)

		if self.media_type(result) is not None:
			return result

		return False

	# get a JSON formatted list of all pending snaps for a user
	def get_snaps(self):
		updates = self.get_updates()
		if updates is None or not updates:
			return False

		conversations = updates['conversations_response']
		result = []
		for conversation in conversations:
			for snap in conversation['pending_received_snaps']:
				snap_readable = {
					'id': snap['id'],
					'media_type': snap['m'],
					'sender': snap['sn'],
					'status': snap['t'],
					'sent': snap['sts'],
					'time': snap['t'],
					'timer': snap['timer'],
					'opened': snap['ts']
				}
				result.append(snap_readable)

		return result
