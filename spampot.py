#! /usr/bin/env python

### spampot.py -- Spam honeypot SMTP server
### Copyright (C) 2003 Neale Pikett <neale@woozle.org>
### Time-stamp: <2003-05-06 09:08:52 neale>
###
### This is free software; you can redistribute it and/or modify it
### under the terms of the GNU General Public License as published by
### the Free Software Foundation; either version 2, or (at your option)
### any later version.
###
### This program is distributed in the hope that it will be useful, but
### WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
### General Public License for more details.
###
### You should have received a copy of the GNU General Public License
### along with this software; see the file COPYING.  If not, write to
### the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139,
### USA.

"""Spam honeypot SMTP server.

This just sits on port 25 of whatever IP you pass in as an argument, and
spools every message out to MAILDIR.  It tries to look like an old
Sendmail server, to maximize chances of being tagged as an open relay.

"""

import cStringIO as StringIO
import asynchat
import asyncore
import syslog
import smtplib
import rfc822
import socket
import time
import sys
import os
import re
import struct
import maildir # get maildir.py from the same place you got this file

# suid to this user
USER = 'root'

# host to relay probes for us
SMARTHOST = '127.0.0.1'

# save multiple messages from the same IP?  You probably don't want this
# -- it can consume a gigabyte a day.
SAVEDUPES = False

# slow down if multiple mails are getting sent over a single connection?
# This could save bandwidth.
TARPIT = True

# chroot to this directory and spool messages there
MAILDIR = '/home/spampot/logs'

# My hostname
HOST = socket.gethostname()

# write to this PID file
PIDFILE = '/var/run/spampot.pid'

# syslog levels (you shouldn't need to change this)
LEVELS = {'info': syslog.LOG_INFO,
          'warning': syslog.LOG_WARNING,
          'error': syslog.LOG_ERR}

###

# Hosts seen
seen = {}

def shescape(str):
    return "'" + str.replace("'", "'\"'\"'") + "'"


class Daemon:
    """Helpful class to make a process a daemon"""

    def __init__(self, pidfile):
        try:
            f = file(pidfile, "r")
            pid = int(f.read())
            f.close()
            os.kill(pid, 0)
            print "Already running at pid %d" % pid
            sys.exit(1)
        except (IOError, OSError, ValueError):
            pass
        self.pidf = file(pidfile, 'w')

    def daemonize(self):
        self.pid = os.fork()
        if self.pid:
            self.pidf.write("%d\n" % self.pid)
            sys.exit(0)
        # Decouple from parent
        self.pidf.close()
        os.chdir("/")
        os.setsid()
        os.umask(0)
        os.close(sys.stdin.fileno())
        os.close(sys.stdout.fileno())
        os.close(sys.stderr.fileno())
        syslog.syslog(syslog.LOG_INFO, "starting")
        return self.pid

    def jail(self, root, user=None, group=None):
        uid, gid = None, None
        if group:
            import grp

            gr = grp.getgrnam(group)
            gid = gr[2]
        if user:
            import pwd

            pw = pwd.getpwnam(user)
            uid = pw[2]
            if not gid: gid = pw[3]
        #os.chroot(root)
        os.chdir('/')
        if gid: os.setgid(gid)
        if uid: os.setuid(uid)


class Listener(asyncore.dispatcher):
    """Listens for incoming socket connections and spins off
    dispatchers created by a factory callable.
    """

    def __init__(self, bindaddr, port,
                 factory, factoryArgs=()):
        asyncore.dispatcher.__init__(self)
        self.factory = factory
        self.factoryArgs = factoryArgs
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((bindaddr, port))
        self.listen(40)
        syslog.syslog(syslog.LOG_INFO, 'Listening on %s:%d' % (bindaddr, port))

    def handle_accept(self):
        # If an incoming connection is instantly reset, eg. by following a
        # link in the web interface then instantly following another one or
        # hitting stop, handle_accept() will be triggered but accept() will
        # return None.
        result = self.accept()
        if result:
            clientSocket, clientAddress = result
            args = [clientSocket] + list(self.factoryArgs)
            self.factory(*args)


class Server(asynchat.async_chat):
    """A stupid SMTP server."""

    def __init__(self, sock):
        self.msg_count = 0
        self.host = 'internal.nat'
        self.request = ''
        self.hello = None
        self.reset()
        asynchat.async_chat.__init__(self)
        self.set_socket(sock)

    def reset(self):
        self.mailfrom = None
        self.rcptto = []

    def log(self, message):
        syslog.syslog(syslog.LOG_INFO, message)

    def log_info(self, message, type='info'):
        lvl = LEVELS.get(type, syslog.LOG_INFO)
        syslog.syslog(lvl, message)

    def handle_connect(self):
        self.peername = self.getpeername()
        self.sockname = self.getsockname()
        self.socknamehex = "%X" % struct.unpack('L', socket.inet_aton(self.sockname[0]))
        self.set_terminator('\r\n')

        self.log('Connect from %s' % (self.peername,))
        now = time.localtime()
        ts = time.strftime('%a, ' + str(now[2]) + ' %b %y %H:%M:%S %Z')
        self.push("220 %s Sendmail ready at %s\r\n" % (self.host, ts))

    def handle_close(self):
        self.log('Close from %s; relayed %d messages' % (self.peername, self.msg_count))
        self.close()

    def collect_incoming_data(self, data):
        self.request += data

    def envelope_found_terminator(self):
        data = self.request
        self.request = ""
        command = data[:4].upper()
        if command in ["HELO", "EHLO"]:
            whom = data[5:].strip()
            self.hello = whom
            self.push("250 Hello %s, pleased to meet you.\r\n" % whom)
        elif command == 'MAIL':
            whom = data[10:].strip()
            self.mailfrom = whom
            self.push("250 %s... Sender ok\r\n" % whom)
        elif command == 'RCPT':
            whom = data[8:].strip()
            self.rcptto.append(whom)
            self.push("250 %s... Recipient ok\r\n" % whom)
        elif command == "DATA":
            self.set_terminator('\r\n.\r\n')
            self.found_terminator = self.data_found_terminator
            self.push('354 Enter mail, end with "." on a line by itself\r\n')
        elif command == "QUIT":
            self.push("221 %s closing connection\r\n" % self.host)
            self.close_when_done()
        elif command == "RSET":
            self.reset()
            self.push('250 Reset state\r\n')
        else:
            self.push("500 Command unrecognized\r\n")
    found_terminator = envelope_found_terminator

    def data_found_terminator(self):
        self.message = self.request
        self.request = ''
        self.set_terminator('\r\n')
        self.found_terminator = self.envelope_found_terminator
        self.deliver_message()
	self.push("250 Mail accepted\r\n")
        self.reset()

    def relay_message(self):
	cmd = "/usr/lib/sendmail -f %s %s" % (shescape(self.mailfrom),' '.join([shescape(s) for s in self.rcptto]))
	#cmd = "/usr/lib/sendmail -f %s %s < /mail" % (shescape(self.mailfrom),' '.join([shescape(s) for s in self.rcptto]))
	#os.system(cmd)
	#self.log(cmd)
        s = os.popen(cmd,'w')
        s.write(self.message)
	#self.log(self.message)
        s.close()

    probe_re = None

    def is_probe(self):
        """Returns true if the current message is a probe message"""
	return True

        # Compile the probe regular expression the first time through
        if not self.probe_re:
            self.probe_re = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|%s:25' % self.socknamehex,
                                       re.IGNORECASE)

        # If it's not the first message this connection, it's probably
        # not a probe.
        if self.msg_count:
            return False

        # Probes also don't have multiple recipients
        if len(self.rcptto) != 1:
            return False

        # And they're short
        if len(self.message) > 1024:
            return False

        # Check for the probe regex
        if self.probe_re.search(self.message):
            # we have a bite: now do some more intense investigation
            f = StringIO.StringIO(self.message)
            m = rfc822.Message(f)

            # IP address in subject?
            subj = m.get('Subject')
            if subj and subj.find(self.sockname[0]) != -1:
                return True

            # Hex-encoded IP address anywhere in message?
            if m.find(self.socknamehex) != -1:
                return True

        return False

    def deliver_message(self):
        global seen

        headers = [
            "SMTP-Date: %s" % time.ctime(),
            "SMTP-Sock: %s:%d" % self.sockname,
            "SMTP-Peer: %s:%d" % self.peername,
            "SMTP-Hello: %s" % self.hello,
            "SMTP-Mail-From: %s" % self.mailfrom,
            "SMTP-Messages-This-Connection: %s" % self.msg_count,
            ]
        for t in self.rcptto:
            headers.append("SMTP-Rcpt-To: %s" % t)
        if self.is_probe():
            self.relay_message()
            self.log('Relayed probe from=%s to=%s' % (self.mailfrom, self.rcptto))
            headers.append("SMTP-Relayed: Yes")
	if(not seen.has_key(self.peername)):
		seen[self.peername] = 0
        msg_count = seen.get(self.peername) + 1
        seen[self.peername] = msg_count
        if msg_count in (0, 1, 2, 3, 4, 8, 64, 512, 4096, 32768, 262144):
            # Hopefully nobody running this will ever hit that last one ;)
            msg = '\r\n'.join(headers) + '\r\n' + self.message
            m = maildir.write(time.strftime('%Y-%m'), msg)
            self.log('Trapped from=%s to=%s msg_count=%d' % (self.mailfrom, self.rcptto, msg_count))
        self.msg_count += 1


def main():
    dmn = Daemon(PIDFILE)
    syslog.openlog('spampot', syslog.LOG_PID, syslog.LOG_MAIL)
    listener = Listener(sys.argv[1], 25, Server)
    dmn.jail(MAILDIR, USER)
    dmn.daemonize()
    asyncore.loop()


if __name__ == '__main__':
    main()

