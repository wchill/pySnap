import tkMessageBox

from Tkinter import *
import tkFileDialog
import pyperclip
from snapchat import Snapchat
from datetime import datetime
import sched
import subprocess
import os
import sys
import pynotify
import psutil
import threading
import time
import signal

PATH = './snaps/'
EXTENSIONS = ['jpeg', 'jpg', 'mp4']


class GUI:
    def __init__(self):
        self.window = Tk()
        self.main_window_init()
        self.client = Snapchat() 
        self.start()

    def start(self):
        self.window.mainloop()

    def main_window_init(self):

        # set window title
        self.window.wm_title('pySnap')

        # configure menu
        menu_bar = Menu(self.window)
        self.window.config(menu=menu_bar)

        # File menu
        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label='Send media', command=self.send_media)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.window.quit)
        menu_bar.add_cascade(label='File', menu=file_menu)

        # Edit menu
        account_menu = Menu(menu_bar, tearoff=0)
        account_menu.add_command(label='Copy Token', command=
            lambda: [pyperclip.copy(self.client.auth_token),
                     tkMessageBox.showinfo('Token copied',
                                           'Auth token copied to clipboard!')])
        account_menu.add_command(label='Logout')
        account_menu.add_command(label='Switch user')
        menu_bar.add_cascade(label='Accounts', menu=account_menu)

        # Prepare the image canvas to be replaced by map image
        self.snap_list = Frame(self.window, width=800, height=600)
        self.snap_list.pack(fill=BOTH, expand=1, side=RIGHT)
        self.window.withdraw()

        w = Toplevel(self.window)
        msg = Label(w, text='Login')
        msg.pack()
        username_panel = PanedWindow(w)
        username_panel.pack(fill=BOTH, expand=1)
        password_panel = PanedWindow(w)
        password_panel.pack(fill=BOTH, expand=1)
        token_panel = PanedWindow(w)
        token_panel.pack(fill=BOTH, expand=1)
        Label(username_panel, text='Username').pack(side=LEFT)
        username_entry = Entry(username_panel)
        username_entry.pack(side=RIGHT)
        Label(password_panel, text='Password').pack(side=LEFT)
        password_entry= Entry(password_panel, show='*')
        password_entry.pack(side=RIGHT)
        Label(token_panel, text='Auth Token').pack(side=LEFT)
        token_entry = Entry(token_panel)
        token_entry.pack(side=RIGHT)
        panel = PanedWindow(w)
        panel.pack()
        ok_btn = Button(panel, text=' OK ', command=lambda: self.login(w, username_entry.get(), password_entry.get(), token_entry.get()))
        ok_btn.pack(side=LEFT)
        cancel_btn = Button(panel, text=' Cancel ', command=lambda: self.cancel_login(w))
        cancel_btn.pack(side=RIGHT)

    def login(self, w, username, password, auth_token):
        w.destroy()
        if password == '':
            if not self.client.login_token(username, auth_token):
                tkMessageBox.showinfo('Failed to login', 'Wrong username or password?')
                self.window.quit()
                return
        else:
            if not self.client.login(username, password):
                tkMessageBox.showinfo('Failed to login', 'Wrong username or password?')
                self.window.quit()
                return
        snaps = self.client.get_snaps()
        if not snaps:
            tkMessageBox.showinfo('Unknown error', 'Something went wrong.')
            self.window.quit()
            return
        Label(self.snap_list, text='Logged in as {0}\n'.format(username)).pack()
        for snap in snaps:
            snap_panel = PanedWindow(self.snap_list)
            snap_panel.pack(fill=X, expand=1)
            Label(snap_panel, text='{0} ({1}s, sent {2})'.format(snap['sender'], snap['time'], datetime.fromtimestamp(snap['sent']/1000))).pack(side=LEFT)
            open_btn = Button(snap_panel, text=' Open ', command=lambda snap=snap: self.open_snap(snap))
            open_btn.pack(side=RIGHT)
        self.window.update()
        self.window.deiconify()

    def cancel_login(self, w):
        w.destroy()
        self.window.quit()

    @staticmethod
    def route_map_callback(filename, data):
        route_map = PhotoImage(file=filename)
        data.configure(image=route_map)
        data.image = route_map

    def send_media(self):
        options = dict(defaultextension='.jpg', filetypes=[('Image file', '.jpg'), ('Video file', '.mp4')],
                       parent=self.window, title='Open media file')
        infile = tkFileDialog.askopenfilename(**options)
        # TODO: add checking for filesizes above 1MB
        if infile:
            self.select_recipients(infile)

    def select_recipients(self, path):
        w = Toplevel(self.window)
        msg = Label(w, text='Select recipients')
        msg.pack()
        recipient_list = Listbox(w, selectmode=MULTIPLE)
        recipients = self.client.friends
        for name in recipients:
            recipient_list.insert(END, name)
        recipient_list.pack(fill=BOTH, expand=1)
        timer_panel = PanedWindow(w)
        timer_panel.pack(fill=BOTH, expand=1)
        Label(timer_panel, text='Send delay (s):').pack(side=LEFT)
        timer_spinbox = Spinbox(timer_panel, from_=0, to=3600, width=6, repeatdelay=200, repeatinterval=5)
        timer_spinbox.pack(side=RIGHT)
        panel = PanedWindow(w)
        panel.pack()
        ok_btn = Button(panel, text=' OK ', command=lambda: self.send_to_recipients(w, recipients, recipient_list.curselection(), path, timer_spinbox.get()))
        ok_btn.pack(side=LEFT)
        cancel_btn = Button(panel, text=' Cancel ', command=w.destroy)
        cancel_btn.pack(side=RIGHT)

    def send_to_recipients(self, w, friends, selected, path, timer_time):
        w.destroy()
        recipient_list = []
        for f in selected:
            recipient_list.append(friends[f])
        if timer_time == 0:
            self.send_helper(path, recipient_list)
        else:
            self.window.after(int(timer_time) * 1000, lambda: self.send_helper(path, recipient_list))

    def send_helper(self, path, recipient_list):
        if self.client.send_snap(path, recipient_list):
            tkMessageBox.showinfo('Send successful', 'Sent {0} to {1} recipient(s)'.format(path, len(recipient_list)))
        else:
            tkMessageBox.showinfo("Failed to send", "An error occurred")

    def open_snap(self, snap):
        dt = datetime.fromtimestamp(snap['sent'] / 1000)
        ext = self.client.media_type(snap['media_type'], binary=False)
        timestamp = str(snap['sent']).replace(':', '-')
        filename = '{}+{}+{}.{}'.format(timestamp, snap['sender'], snap['id'], ext)
        path = PATH + filename
        if not os.path.isfile(path):
            data = self.client.get_snap(snap['id'])
            with open(path, 'wb') as outfile:
                outfile.write(data)

        snap['path'] = path
        file_path = snap['path']

        # open /dev/null or equivalent so we can redirect stdout/stderr to it
        nullfile = open(os.devnull, 'w')
        scheduler = sched.scheduler(time.time, time.sleep)

        if sys.platform.startswith('linux'):
            p = subprocess.Popen(['xdg-open', file_path], stdout=nullfile, stderr=nullfile, preexec_fn=os.setsid)
        elif sys.platform.startswith('darwin'):
            p = subprocess.Popen(['open', file_path], stdout=nullfile, stderr=nullfile)
        elif sys.platform.startswith('win'):
            p = subprocess.Popen(['start /WAIT', file_path], stdout=nullfile, stderr=nullfile)
        else:
            print 'I don\'t recognize your operating system: {0}'.format(sys.platform)
        self.window.after(snap['time'] * 1000 + 1000, lambda: self.mark_read(snap, p))
        '''
        scheduler.enter(snap['time'], 1, self.mark_read, (snap, p))
        t = threading.Thread(target=lambda: scheduler.run)
        t.start()
        '''

    def mark_read(self, snap, p):
        print 'marking read'
#        self.client.mark_read(snap)
        os.remove(snap['path'])
        if sys.platform.startswith('linux'):
            os.killpg(p.pid, signal.SIGTERM)
        elif sys.platform.startswith('win'):
            p.kill()

if __name__ == '__main__':
    GUI()
