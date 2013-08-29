#!/usr/bin/env python

# to be run as a cron job to update the data

from mensanotify import mensa

if __name__ == '__main__':
    mensa.data.update()
