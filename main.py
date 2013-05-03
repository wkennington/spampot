#!/usr/bin/env python3
"""
    Spampot Runner Application
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
import smtp
import configparser

def run():
    config = configparser.ConfigParser()
    config.read('spampot.conf')
    if not ('Global' in config.sections()):
        print('Configuration file is missing the "Global" section')
        exit(1)
    server = smtp.SMTP()
    exit(0)

if  __name__ == '__main__':
    run()
