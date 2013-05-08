"""
    Spampot Probe Mail Handler
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
import subprocess

class Handler(mh.base.Handler):
    _deps = {'Store'}

    def __init__(self, log, config):
        self.log = log
        self.config = config
        self.sendmail = config.get('sendmail', '/usr/lib/sendmail')

    def startup(self, handlers):
        self.handlers = handlers

    def shutdown(self):
        pass

    def handle(self, host, port, msg):
        self.send(host, msg)

    def send(self, host, msg):
        cmd = [self.sendmail, '-f', msg.sender] + msg.to
        read, write = os.pipe()
        os.write(write, msg.data)
        os.close(write)
        ret = subprocess.call(cmd, shell=False, stdin=read)
        os.close(read)
        if ret == 0:
            self.log.debug('PROBE: Sent mail from %s' % host)
        else:
            self.log.warning('PROBE: Failed to send smtp message %s' % host)
