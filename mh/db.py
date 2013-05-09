"""
    Spampot Database Storage
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
import shelve

class Handler(mh.base.Handler):
    _deps = {}

    def __init__(self, log, config):
        self.log = log
        self.config = config
        self.db = config.get('file', 'db')

    def startup(self, handlers):
        self.handlers = handlers
        try:
            self.shelf = shelve.open(self.db, writeback=False)
        except Exception as e:
            self.log.error('DB %s: %s' % (self.db, e))
            exit(1)

    def shutdown(self):
        self.shelf.close()

    def handle(self, host, port, msg):
        pass

    def __getitem__(self, idx):
        return self.shelf.__getitem__(idx)
    def __setitem__(self, idx, val):
        return self.shelf.__setitem__(idx, val)
