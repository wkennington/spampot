"""
    Spampot Mail Handler Template
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

class Handler:
    __deps = {}

    def __init__(self, log, config):
        self.log = log
        self.config = config

    def __lt__(self, other):
        if self.__name in other.__deps:
            if other.__name in self.__deps:
                raise Exception('Circular Dependency')
            return False
        return True

    def startup(self, handlers):
        self.handlers = handlers

    def shutdown(self):
        pass

    def handle(self, host, port, msg):
        self.log.debug('UNNAMED: Default Handler Action')
