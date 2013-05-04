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

import asyncore
import socket

class SMTPHandler(asyncore.dispatcher_with_send):
    def __init__(self, sock, log):
        asyncore.dispatcher_with_send.__init__(self, sock)
        self.buff = b''
        self.log = log

    def handle_read(self):
        data = self.recv(8192)
        if data:
            self.buff += data
            idx = self.buff.find(b'\r\n')
            while idx > 0:
                self.cmd(self.buff[:idx])
                self.buff = self.buff[idx+2:]
                idx = self.buff.find(b'\r\n')

    def cmd(self, data):
        self.log.info('Got CMD: %s' % data)

class SMTP(asyncore.dispatcher):
    def __init__(self, log, addr='0.0.0.0', port=25, host='localhost'):
        self.log = log
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((addr, port))
        self.listen(10)

    def handle_accepted(self, sock, addr):
        self.log.info('Connection from %s' % str(addr))
        handler = SMTPHandler(sock, self.log)

    def run(self):
        asyncore.loop()

    def cleanup(self):
        self.close()
