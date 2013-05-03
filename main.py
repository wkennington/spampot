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
import argparse

def serve(log, config):
    addr = config['Global'].get('addr', '0.0.0.0')
    port = config['Global'].get('port', 25)
    host = config['Global'].get('host', 'localhost')
    server = smtp.SMTP(host=host, port=port, addr=addr)
    server.run()
    exit(0)

def daemonize(log_name, config):
    if log_name == '-':
        pass
    pass

def normal(log_name, config):
    pass

def run():
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description='Spawn the spampot server')
    parser.add_argument('--conf', dest='conf', metavar='c', type=str, default='spampot.conf', help='Configuration file to read')
    args = parser.parse_args()

    # Read the default configuration file
    config = configparser.ConfigParser()
    config.read(args.conf)
    if not ('Global' in config.sections()):
        print('Configuration file is missing the "Global" section')
        exit(1)
    log = config['Global'].get('log', 'syslog')

    # Perform the requested service
    if config['Global'].get('daemon', True):
        daemonize(log, config)
    else:
        normal(log, config)

    exit(0)

if  __name__ == '__main__':
    run()
