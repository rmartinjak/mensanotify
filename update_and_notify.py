#!/usr/bin/env python

# to be run as a cron job to send out notifications

from mensanotify import mensa, users
from mensanotify.email import send_results

def send_all_notifications():
    for k, v in users.items():
        results = mensa.search_many(v.queries, v.mensae)
        if results:
            send_results(k, results)

if __name__ == '__main__':
    mensa.data.update()
    send_all_notifications()
