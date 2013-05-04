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
import os, sys
import signal
import configparser
import argparse
import logging, logging.handlers
import pwd, grp

def death(pidfile, log, server):
    if pidfile != None:
        os.unlink(pidfile)
    server.cleanup()
    exit(0)

def serve(log, config):
    log.debug('Opening Server')

    # Setup operations based on the pidfile
    pidfile = config['Global'].get('pidfile', None)
    if pidfile != None:
        if os.path.isfile(pidfile):
            log.error('Pidfile already exists! Exiting')
            exit(1)
        open(pidfile, 'w').write(str(os.getpid()))
        log.debug('Wrote pidfile %s' % pidfile)

    # Create a new SMTP Server
    addr = config['Global'].get('addr', '0.0.0.0')
    port = config['Global'].get('port', 25)
    host = config['Global'].get('host', 'localhost')
    server = smtp.SMTP(log, host=host, port=port, addr=addr)

    # Setup the kill signal
    signal.signal(signal.SIGINT, (lambda signum, frame: death(pidfile, log, server)))

    # Run the server
    log.info('Accepting Connections on %s:%d', addr, port)
    log.info('Using Hostname %s', host)
    while True:
        server.run()
    death(pidfile, log, server)

def daemonize(log, config):
    log.debug('Forking Daemon')

    # Perform the first fork
    try: 
        pid = os.fork() 
        if pid > 0:
            exit(0) 
        log.debug('First Fork to pid %d' % pid)
    except OSError as e:
        log.error('Failed to fork daemon process')
        exit(1)

    # Decouple from parent environment
    os.chdir("/") 
    os.setsid() 
    os.umask(0)

    # Drop user / group permissions
    udown = config['Global'].get('user', None)
    gdown = config['Global'].get('group', None)
    try:
        if udown != None:
            uid = pwd.getpwnam(udown).pw_uid
        if gdown != None:
            gid = grp.getgrnam(gdown).gr_gid
    except:
        log.error('Failed to get User / Group Ids. Maybe they don\'t exist?')
        exit(1)
    try:
        if gdown != None:
            os.setgid(gid)
        if udown != None:
            os.setuid(uid)
    except:
        log.error('Cannot Drop User / Group Privileges. Probably not running as root?')
        exit(1)

    # Perform the second fork
    try: 
        pid = os.fork() 
        if pid > 0:
            exit(0) 
        log.debug('Second Fork to pid %d' % pid)
    except OSError as e:
        log.error('Failed to fork daemon process')
        exit(1) 

    # Begin Execution
    serve(log, config) 

def normal(log, config):
    serve(log, config)

def run():
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description='Spawn the spampot server')
    parser.add_argument('--conf', '-c', dest='conf', metavar='c', type=str, default='spampot.conf', help='Configuration file to read')
    parser.add_argument('--daemon', '-d', dest='daemon', action='store_const', const=True, default=None, help='False to serve in current process or True to spawn workers')
    parser.add_argument('--no-daemon', '-n', dest='daemon', action='store_const', const=False, default=None, help='False to serve in current process or True to spawn workers')
    parser.add_argument('--log-level', '-L', metavar='L', dest='log_level', type=str, default=None, help='Level of Logging to display')
    parser.add_argument('--log', '-l', dest='logs', metavar='file', type=str, default=None, nargs='+', help='The logfile[s] to write into')
    args = parser.parse_args()

    # Read the default configuration file
    config = configparser.ConfigParser()
    config.read(args.conf)
    if not ('Global' in config.sections()):
        print('Configuration file is missing the "Global" section')
        exit(1)

    # Merge config with command line arguments
    logs = args.logs if args.logs else config['Global'].get('log', 'syslog').split(' ')
    log_level = args.log_level if args.log_level else config['Global'].get('log_level', 'INFO').upper()
    daemon = args.daemon if args.daemon != None else config['Global'].get('daemon', True)

    # Setup the logger
    logger = logging.getLogger('Global')
    logger.setLevel(log_level)
    if daemon and logs == ['-']:
        logs = ['syslog']
    for log in logs:
        if log == 'syslog':
            logger.addHandler(logging.handlers.SysLogHandler())
        elif log == '-' and not daemon:
            logger.addHandler(logging.StreamHandler(sys.stdout))
        else:
            logger.addHandler(logging.handlers.RotatingFileHandler(log))

    # Debugging Log Output
    logger.warning('Using Log Level %s' % log_level)
    logger.debug('Effective Log Level %d' % logger.getEffectiveLevel())
    logger.info('Spawning as %s' % ('daemon' if daemon else 'normal'))

    # Perform the requested service
    daemonize(logger, config) if daemon else normal(logger, config)

    exit(0)

if  __name__ == '__main__':
    run()