import locale
import datetime

ISO_FORMAT = '%Y-%m-%d'


def from_string(datestr, fmt, source_locale):
    old_loc = locale.getlocale()
    try:
        locale.setlocale(locale.LC_TIME, (source_locale, 'UTF-8'))
        d = datetime.datetime.strptime(datestr, fmt).date()
    finally:
        locale.setlocale(locale.LC_TIME, old_loc)
    return from_date(d)


def from_date(dt):
    return dt.strftime(ISO_FORMAT)


def to_weekday(iso_date, dest_locale=None):
    dt = datetime.datetime.strptime(iso_date, ISO_FORMAT)
    return dt.strftime('%A')
