from snapchat import Snapchat
import getpass

PATH = './snaps/'
EXTENSIONS = ['jpeg', 'jpg', 'mp4']
USERNAME = None
PASSWORD = None

s = Snapchat()
if USERNAME is None:
    USERNAME = raw_input('username: ')
if PASSWORD is None:
    PASSWORD = getpass.getpass('password: ')
s.login(USERNAME, PASSWORD)
s.send_snap(0, 'sc.png', '')
snaps = s.get_snaps()
for snap in snaps:
    data = s.get_snap(snap['id'])
    if data:
        ext = s.media_type(data)
        timestamp = str(snap['sent']).replace(':', '-')
        filename = '{}+{}+{}.{}'.format(timestamp, snap['sender'], snap['id'], ext)
        path = PATH + filename
        with open(path, 'wb') as outfile:
            outfile.write(data)
