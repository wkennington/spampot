# maildir.py -- Maildir utilities
#
# Released into the public domain

"""Maildir utilities"""

__author__ = 'Neale Pickett <neale@woozle.org>'

import os
import socket
import time

# Counter gets incremented by one for every message delivered
count = 0

# Local hostname
HOST = socket.gethostname()

def create(mdir):
    os.umask(0022)
    for i in ('tmp', 'cur', 'new'):
        os.makedirs('%s/%s' % (mdir, i))

def write(mdir, message, info=None):
    """Write a message out to a maildir.

    """
    global count

    mdir = time.strftime('%Y-%m')
    if not os.path.exists(mdir):
        create(mdir)

    filename = '%d.%d_%04d.%s' % (time.time(), os.getpid(),
                                  count, HOST)
    f = open('%s/tmp/%s' % (mdir, filename),
             'w')
    f.write(message)
    f.close()
    if info:
        os.rename('%s/tmp/%s' % (mdir, filename),
                  '%s/cur/%s:2,%s' % (mdir, filename, info))
    else:
        os.rename('%s/tmp/%s' % (mdir, filename),
                  '%s/new/%s' % (mdir, filename))
    count += 1
