"""
    Spampot SMTP Server Implementation
    Copyright (C) 2013 William A. Kennington III

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import asyncore, asynchat
import socket
import mail
import time

class SMTPHandler(asynchat.async_chat):
    def pushs(self, msg):
        self.push(msg.encode('utf-8'))

    def __init__(self, sock, log, handlers, host):
        self.found_terminator = header_found_terminator
        asynchat.async_chat.__init__(self, sock=sock)
        self.peeraddr = str(self.getpeername())
        self.peername = None
        self.set_terminator(b'\r\n')
        self.msg_count = 0
        self.buff = b''
        self.log = log
        self.handlers = handlers
        self.host = host
        self.reset()

        self.log.debug('Connection from %s' % self.peeraddr)
        self.pushs('220 %s ESMTP Sendmail 8.14.7\r\n' % self.host)

    def reset(self):
        self.msg = mail.Msg(to=[], sender=None, data=None)

    def handle_close(self):
        if self.msg_count == 0:
            self.log.info('Closed with no messages from %s' % self.peeraddr)
        else:
            self.log.info('Processed %d messages from %s' % (self.msg_count, self.peername))
        self.close()

    def collect_incoming_data(self, data):
        self.buff += data

    def parseKeyword(self, args, key):
        args = args.strip()
        idx = args.find(key)
        return None if idx == -1 else args[idx+len(key):].strip()

    def header_found_terminator(self):
        # Get the data
        data = self.buff
        self.buff = b''

        # Get the command and arguments
        idx = data.find(b' ')
        cmd = (data if idx == -1 else data[:idx]).upper()
        args = (b'' if idx == -1 else data[idx+1:]).decode('utf-8')

        # Handle Possible Commands
        if cmd in [b'HELO', b'EHLO']:
            self.peername = args
            self.log.debug('%s is named %s' % (self.peeraddr, self.peername))
            self.pushs('250 Hello %s, please to meet you\r\n' % self.peername)
        elif command == b'MAIL':
            act = self.parseKeyword(args, 'FROM:')
            if act == None:
                self.log.debug('%s sent invalid mail cmd: %s' % (self.peeraddr, args))
                self.pushs('500 Invalid Params\r\n')
            else:
                self.log.debug('%s mail from %s' % (self.peeraddr, act))
                self.msg.sender = act
                self.pushs('250 Ok\r\n')
        elif command == b'RCPT':
            act = self.parseKeyword(args, 'TO:')
            if == None:
                self.log.debug('%s invalid rcpt cmd: %s' % (self.peeraddr, args))
                self.pushs('500 Invalid Params\r\n')
            else:
                self.log.debug('%s added rcpt %s' % (self.peeraddr, act))
                self.msg.to.append(act)
                self.pushs('250 Ok\r\n')
        elif command == b'DATA':
            self.pushs('354 Enter mail, end with "." on a line by itself\r\n')
            self.log.debug('%s now sending data' % self.peeraddr)
            self.set_terminator(b'\r\n.\r\n')
            self.found_terminator = data_found_terminator
        elif command == b'QUIT':
            self.pushs('221 %s closing connection\r\n' % self.host)
            self.log.debug('%s quit' % self.peeraddr)
            self.close_when_done()
        elif command == b'RSET':
            self.reset()
            self.log.debug('%s reset state' % self.peeraddr)
            self.pushs('250 Reset state\r\n')
        else:
            self.pushs('500 Command unrecognized\r\n')
            self.log.debug('%s sent invalid command: %s' % (self.peeraddr, cmd))

    def data_found_terminator(self):
        self.set_terminator(b'\r\n')
        self.found_terminator = header_found_terminator
        

class SMTP(asyncore.dispatcher):
    def __init__(self, log, addr='0.0.0.0', port=25, host='localhost'):
        self.log = log
        self.handlers = []
        self.host = host
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((addr, port))
        self.listen(10)

    def handle_accepted(self, sock, addr):
        SMTPHandler(sock, self.log, self.handlers, self.host)

    def add_handler(self, handler):
        self.handlers.append(handler)

    def run(self):
        asyncore.loop()

    def cleanup(self):
        self.close()
