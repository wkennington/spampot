"""
    Spampot Storage Mail Handler
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

import mh.base
import os
import datetime

class Handler(mh.base.Handler):
    _deps = {'DB'}

    def __init__(self, log, config):
        self.log = log
        self.config = config
        self.mdir = config.get('dir', None)
        if self.mdir == None:
            log.error('STORE: No mail directory configured')
            exit(1)
        if os.path.isdir(self.mdir):
            log.debug('STORE: Using mail directory %s' % self.mdir)
        else:
            log.error('STORE: Mail directory %s doesn\'t exist' % self.mdir)
            exit(1)

    def startup(self, handlers):
        self.handlers = handlers

    def shutdown(self):
        pass

    def handle(self, host, port, msg):
        data = ('MAIL FROM: %s\r\n' % msg.sender).encode('utf-8')
        for to in msg.to:
            data += ('RCPT TO: %s\r\n' % to).encode('utf-8')
        data += b'DATA\r\n' + msg.data + b'\r\n.\r\n'
        self.save(host, data)

    def createDir(self, d):
        try:
            if not os.path.isdir(d):
                if os.path.exists(d):
                    os.unlink(d)
                os.mkdir(d)
            return True
        except:
            self.log.error('STORE: Failed to create mail directory %s', d)
            return False

    def save(self, host, data):
        now = datetime.datetime.now()
        adir = '%s/%s' % (self.mdir, host)
        ddir = '%s/%s' % (adir, now.strftime('%m-%d-%y'))
        if (not self.createDir(adir)) or (not self.createDir(ddir)):
            return

        try:
            fname = '%s/%s' % (ddir, now.strftime('%H:%M:%S.%f'))
            f = open(fname, 'wb')
            f.write(data)
            f.close()
            self.log.debug('STORE: Saved message from %s to %s' % (host, fname))
        except:
            self.log.error('STORE: Failed to write message to %s' % fname)
