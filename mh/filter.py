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
    _deps = {'DB'}

    def __init__(self, log, config):
        self.log = log
        self.config = config
        self.forwardCount = int(config.get('forwardCount', '5'))

    def startup(self, handlers):
        self.handlers = handlers
        self.newmsg = False
        self.newIP = False

    def shutdown(self):
        pass

    # Is essentially using the db as a keystore to look up if we've seen a
    # message before
    def handle(self, host, port, msg):
        #self.log.debug('UNNAMED: Filter Handler Action')
        hashd = hashlib.sha256(data).hexdigest()
        if not self.handlers['DB'].shelf.has_key("HASH:" + hashd):
            self.handlers['DB'].shelf["HASH:" + hashd] = True
            self.newmsg = True
        if self.handlers['DB'].shelf.has_key("IP:" + host):
            ipcnt = self.handlers['DB'].shelf["IP:" + host]
            if ipcnt <= self.forwardCount:
                self.newIP = True
            self.handlers['DB'].shelf["IP:" + host] = ipcnt + 1
        else:
            self.handlers['DB'].shelf["IP:" + host] = 1
            self.newIP = True
