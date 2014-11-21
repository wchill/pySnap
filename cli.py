from datetime import datetime
import os
import sys
import subprocess
import getpass
import sched
import time
import threading
import psutil
import signal
import pynotify
import Queue

from snapchat import Snapchat


PATH = './snaps/'
EXTENSIONS = ['jpeg', 'jpg', 'mp4']


def cli():
    clear()
    s = Snapchat()
    username = raw_input('Please enter username: ')
    if not sys.platform.startswith('win'):
        password = getpass.getpass('Please enter password: ')
    else:
        password = raw_input('Please enter password (empty for token entry): ')
    if password == '':
        auth_token = raw_input('Please enter auth token: ')
        if not s.login_token(username, auth_token):
            raw_input('Invalid username/auth token combo')
            clear()
            exit()
    else:
        if not s.login(username, password):
            raw_input('Invalid username/password combo')
            clear()
            exit()

    pynotify.init("pySnap")
    queue = Queue.Queue()
    bg_scheduler = sched.scheduler(time.time, time.sleep)
    bg_scheduler.enter(300, 1, check_snaps, (s, bg_scheduler, queue))
    bg_check = threading.Thread(target=bg_scheduler.run)
    bg_check.setDaemon(True)
    bg_check.start()
    snaps = s.get_snaps()
    user_input = None
    functions = {
        'R': lambda: s.get_snaps(),
        'S': send
    }
    clear()
    while user_input != 'X':
        print 'Welcome to Snapchat!'
        print 'Logged in as {0} (token {1})'.format(username, s.auth_token)
        print
        print '{0} pending snaps:'.format(len(snaps))
        num = 1
        for snap in snaps:
            #print snap
            #print snap['media_type']
            dt = datetime.fromtimestamp(snap['sent'] / 1000)
            ext = s.media_type(snap['media_type'], binary=False)
            timestamp = str(snap['sent']).replace(':', '-')
            filename = '{}+{}+{}.{}'.format(timestamp, snap['sender'], snap['id'], ext)
            path = PATH + filename

            # check if file already exists so we don't need to redownload
            '''
            if not os.path.isfile(path):
                data = s.get_snap(snap['id'])
                with open(path, 'wb') as outfile:
                    outfile.write(data)
            '''

            snap['path'] = path
            print '[{0}] Snap from {1} ({2}s, Sent {3})'.format(num, snap['sender'], snap['time'], dt)
            num += 1
        print
        print '[R] - refresh snaps'
        print '[S] - send a snap'
        print '[X] - exit'
        user_input = raw_input('Enter an option: ').upper()
        num_input = int(user_input) if user_input.isdigit() else None
        if len(snaps) >= num_input > 0:
            dt = datetime.fromtimestamp(snap['sent'] / 1000)
            ext = s.media_type(snap['media_type'], binary=False)
            timestamp = str(snap['sent']).replace(':', '-')
            filename = '{}+{}+{}.{}'.format(timestamp, snap['sender'], snap['id'], ext)
            path = PATH + filename
            snap = snaps[num_input - 1]
            if not os.path.isfile(path):
                data = s.get_snap(snap['id'])
                with open(path, 'wb') as outfile:
                    outfile.write(data)

            snap['path'] = path
            file_path = snap['path']

            # open /dev/null or equivalent so we can redirect stdout/stderr to it
            nullfile = open(os.devnull, 'w')

            # cross-platform method to open a media file
            p = None
            scheduler = sched.scheduler(time.time, time.sleep)
#            try:
            if True:
                if sys.platform.startswith('linux'):
                    p = subprocess.Popen(['xdg-open', file_path], stdout=nullfile, stderr=nullfile, preexec_fn=os.setsid)
                elif sys.platform.startswith('darwin'):
                    p = subprocess.Popen(['open', file_path], stdout=nullfile, stderr=nullfile)
                elif sys.platform.startswith('win'):
                    p = subprocess.Popen(['start /WAIT', file_path], stdout=nullfile, stderr=nullfile)
                else:
                    print 'I don\'t recognize your operating system: {0}'.format(sys.platform)
                scheduler.enter(snap['time'], 1, mark_read, (s, snap, p, queue))
                t = threading.Thread(target=scheduler.run)
                t.start()
#            except:
#                print 'Uh oh, I was unable to open the file.'

        elif user_input in functions:
            if user_input == 'R':
                queue.put(functions[user_input]())
                print 'Refreshed!'
            else:
                functions[user_input](s)
        elif user_input != 'X':
            print 'I don\'t recognize that command.'

        if user_input != 'X':
            raw_input('Press enter to continue...')
            clear()

        if not queue.empty():
            while not queue.empty():
                buf = queue.get()
            new_snaps = []
            for st in buf:
                found = False
                for snap in snaps:
                    if st['id'] == snap['id']:
                        found = True
                        break
                if found == True:
                    new_snaps.append(st)
            for snap in new_snaps:
                title = 'New snap from {0}!'.format(snap['sender'])
                dt = datetime.fromtimestamp(snap['sent'] / 1000)
                message = '{0} seconds, sent {1}'.format(snap['time'], dt)
                notice = pynotify.Notification(title, message)
                notice.show()
    #        snaps = buf 
    sys.exit(0)

def mark_read(s, snap, p, queue):
    print 'marking read'
#    s.mark_read(snap)
    print 'removing file'
    os.remove(snap['path'])
    # TODO: figure out cross platform way to kill process
    print 'killing viewer'
    if sys.platform.startswith('linux'):
        os.killpg(p.pid, signal.SIGTERM)
    elif sys.platform.startswith('win'):
        p.kill()
    queue.put(s.get_snaps())

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
    recipients = secondary_input.lower().split(',')
    if s.send_snap(path, recipients):
        print 'Sent {0} to {1}'.format(path, recipients)
    else:
        print 'Error sending snap'


# clears the terminal and resets scroll position to top left
# using ANSI escape characters
def clear():
    if sys.platform.startswith('linux'):
        print chr(27) + "[2J" + chr(27) + "[H"

def check_snaps(s, scheduler, queue):
    scheduler.enter(300, 1, check_snaps, s, scheduler, queue)
    queue.put(s.get_snaps())

if __name__ == '__main__':
    cli()
