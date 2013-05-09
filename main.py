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

import collections
import csmtp, pysmtp
import os, sys
import glob
import signal
import configparser
import argparse
import logging, logging.handlers
import pwd, grp

def toBool(s):
    return s.lower() in ['true', 't', '1', 'yes', 'y']

def death(pidfile, log, server, handlers=None):
    if pidfile != None:
        os.unlink(pidfile)
    server.cleanup()
    if handlers:
        for k in reversed(handlers):
            handlers[k].shutdown()
            log.debug('Shutdown %s', k)
    log.info('Closing Cleanly')
    exit(0)

def serve(log, config, handlers):
    log.debug('Opening Server')

    # Setup operations based on the pidfile
    pidfile = config['Global'].get('pidfile', None)
    if pidfile != None:
        if os.path.exists(pidfile):
            try:
                with open(pidfile, 'r') as f:
                    pid = int(f.read())
                os.kill(pid, 0)
                log.error('Pidfile already exists! Exiting')
                exit(1)
            except OSError:
                log.info('Cleaning stale pidfile %s' % pidfile)
                os.unlink(pidfile)

        with open(pidfile, 'w') as f:
            f.write(str(os.getpid()))
        log.debug('Wrote pidfile %s' % pidfile)

    # Create a new SMTP Server
    addr = config['Global'].get('addr', '0.0.0.0')
    port = int(config['Global'].get('port', '25'))
    host = config['Global'].get('host', 'localhost')
    try:
        if toBool(config['Global'].get('custom_handler', 'False')):
            log.info('Using custom SMTP Server')
            obj = csmtp.SMTP
        else:
            log.info('Using built-in SMTP Server')
            obj = pysmtp.SMTP
        server = obj(log, host=host, port=port, addr=addr, handlers=handlers)
    except:
        log.error('Failed to bind server to socket %s:%d' % (host, port))
        exit(1)

    # Setup the kill signal
    diefun = (lambda signum, frame: death(pidfile, log, server, handlers))
    signal.signal(signal.SIGINT, diefun)
    signal.signal(signal.SIGTERM, diefun)

    # Chroot directory if necessary
    chroot = config['Global'].get('chroot', None)
    if chroot != None:
        try:
            os.chroot(chroot)
            log.info('Chrooted into %s' % chroot)
        except:
            log.error('Failed to Chroot into %s' % chroot)

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
            log.info('Dropped group privileges to %s' % gdown)
            os.setgid(gid)
        if udown != None:
            log.info('Dropped user privileges to %s' % udown)
            os.setuid(uid)
    except:
        log.error('Cannot Drop User / Group Privileges. Probably not running as root?')
        exit(1)

    # Run the server
    log.info('Accepting Connections on %s:%d', addr, port)
    log.info('Using Hostname %s', host)
    while True:
        server.run()
    death(pidfile, log, server, handlers)

def daemonize(log, config, handlers):
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
    serve(log, config, handlers)

def normal(log, config, handlers):
    serve(log, config, handlers)

def run():
    # Change into the script directory
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    # Parse the command line arguments
    parser = argparse.ArgumentParser(description='Spawn the spampot server')
    parser.add_argument('--conf', '-c', dest='conf', metavar='c', type=str, default='spampot.conf', help='Configuration file to read')
    parser.add_argument('--daemon', '-d', dest='daemon', action='store_const', const=True, default=None, help='False to serve in current process or True to spawn workers')
    parser.add_argument('--no-daemon', '-n', dest='daemon', action='store_const', const=False, default=None, help='False to serve in current process or True to spawn workers')
    parser.add_argument('--log-level', '-L', metavar='L', dest='log_level', type=str, default=None, help='Level of Logging to display')
    parser.add_argument('--log', '-l', dest='logs', metavar='file', type=str, default=None, nargs='+', help='The logfile[s] to write into')
    args = parser.parse_args()

    try:
        # Read the default configuration file
        config = configparser.ConfigParser()
        config.read(args.conf)
        if not ('Global' in config.sections()):
            print('Configuration file is missing the "Global" section')
            exit(1)

        # Read additional configuration files
        config_dir = config['Global'].get('config_dir', None)
        if config_dir != None:
            for conf in glob.glob('%s/*.conf' % config_dir):
                config.read(conf)
    except configparser.ParsingError as e:
        print('%s' % e, file=sys.stderr)
        exit(1)

    # Merge config with command line arguments
    logs = args.logs if args.logs else config['Global'].get('log', 'syslog').split(' ')
    log_level = args.log_level if args.log_level else config['Global'].get('log_level', 'INFO').upper()
    daemon = args.daemon if args.daemon != None else toBool(config['Global'].get('daemon', 'True'))

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

    # Setup additional handlers
    handlerl = {}
    hset = [x for x in config.sections() if x.lower() != 'global' and toBool(config[x].get('Enabled', 'False'))]
    for h in hset:
        mod = __import__('mh.%s' % h.lower(), fromlist=['Handler'])
        handler = getattr(mod, 'Handler')(logger, config[h])
        handler._name = h
        try:
            handler._deps
        except:
            handler._deps = {}
        handlerl[h] = handler
        logger.debug('Loaded handler %s' % h)
    for k,v in handlerl.items():
        for d in v._deps:
            if not d in handlerl:
                logger.error('%s couldn\'t satisfy dependency %s' % (k, d))
                exit(1)
    handlers = collections.OrderedDict(sorted(handlerl.items(), key=lambda t: t[1]))
    for k,v in handlers.items():
        v.startup(handlers)
        logger.info('Starting handler %s' % k)

    # Perform the requested service
    logger.info('Spawning as %s' % ('daemon' if daemon else 'normal'))
    daemonize(logger, config, handlers) if daemon else normal(logger, config, handlers)

    exit(0)

if  __name__ == '__main__':
    run()
