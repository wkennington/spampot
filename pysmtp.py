"""
    Spampot Python Built-In SMTP Server Implementation
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
import smtpd
import mail

class SMTP(smtpd.SMTPServer):
    def __init__(self, log, addr='0.0.0.0', port=25, host='localhost'):
        smtpd.SMTPServer.__init__(self, (addr, port), None)
        self.log = log

    def run(self, handlers=[]):
        self.handlers = handlers
        asyncore.loop()

    def process_message(self, peer, sender, to, data):
        host, port = peer
        self.log.debug('PYSMTP: %s got message contents' % host)
        bdata = data.encode('utf-8')
        for k,v in self.handlers.items():
            self.log.debug('PYSMTP: %s called handler %s' % (host, k))
            v.handle(host, port, mail.Msg(to, sender, bdata))

    def cleanup(self):
        self.close()
