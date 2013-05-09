"""
    Spampot Base Handler Template
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
import hashlib

class Handler(mh.base.Handler):
    _deps = {'db'}

    def __init__(self, log, config):
        self.log = log
        self.config = config
        self.forwardCount = int(config.get('forwardCount', '5'))

    def startup(self, handlers):
        self.handlers = handlers

    def shutdown(self):
        pass

    # Is essentially using the db as a keystore to look up if we've seen a
    # message before
    def handle(self, host, port, msg):
        self.newmsg = False
        self.newIP = False

        # Check message hash to see if it is unique
        hashd = 'HASH:%s' % hashlib.sha256(msg.data).hexdigest()
        if not hashd in self.handlers['db'].shelf:
            self.handlers['db'].shelf[hashd] = True
            self.newmsg = True

        # Check how many times we've seen this client IP
        ip = 'IP:%s' % host
        if ip in self.handlers['db'].shelf:
            ipcnt = self.handlers['db'].shelf[ip]
            if ipcnt <= self.forwardCount:
                self.newIP = True
            self.handlers['db'].shelf[ip] = ipcnt + 1
        else:
            self.handlers['db'].shelf[ip] = 1
            self.newIP = True
