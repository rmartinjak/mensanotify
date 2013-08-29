#!/usr/bin/env python

# to be run as a cron job to send out notifications

from mensanotify import mensa, users
from mensanotify.email import send_results

if __name__ == '__main__':
    for k, v in users.items():
        results = mensa.search_many(v.queries, v.mensae)
        if results:
            send_results(k, results)
