# -*- coding: utf-8 -*-
"""

    iso8601
    ~~~~~~~

    Converts string to datetime objet.

    :copyright: (c) 2013 by Xavier Barbosa.
    :license: BSD, see LICENSE for more details.
"""

import datetime
import re
import time
from decimal import Decimal

__all__ = [
    'parse',
]

iso_date_extended = r'''(?P<date>
    (?P<year>\d{4})
    (
        (   # month-day
            -(?P<month>\d{2})
            (
                -(?P<day>\d{2})
            )?
        )
        |
        (   # ordinal day
            -(?P<day_ord>\d{3})
        )
        |
        (   # week-day
            -W(?P<week>\d{2})
            (
                -(?P<week_day>\d{1})
            )?
        )
    )?
)'''

iso_date = r'''(?P<date>
    (?P<year>\d{4})
    (
        (   # month-day
            (?P<month>\d{2})
            (?P<day>\d{2})?
        )
        |
        (   # ordinal day
            (?P<day_ord>\d{3})
        )
        |
        (   # week-day
            W(?P<week>\d{2})
            (?P<week_day>\d{1})?
        )
    )?
)'''

iso_tz_glob = r'''(?P<tz>
    (
        Z
        |
        (
            (?P<direction>[+-])
            (?P<hour>\d{2})
            (
                :?(?P<min>\d{2})
            )?
        )
    )
)'''

iso_tz_extended = r'''(?P<tz>
    (
        Z
        |
        (
            (?P<tz_direction>[+-])
            (?P<tz_hour>\d{2})
            (
                :(?P<tz_min>\d{2})
            )?
        )
    )
)'''

iso_tz = r'''(?P<tz>
    (
        Z
        |
        (
            (?P<tz_direction>[+-])
            (?P<tz_hour>\d{2})
            (?P<tz_min>\d{2})?
        )
    )
)'''

iso_time_extended = r'''(?P<time>
    (?P<hour>\d{2})
    (
        :(?P<min>\d{2})
        (
            :(?P<sec>\d{2})
            (
                [,.](?P<sub_sec>\d+)
            )?
        )?
    )?
)
'''

iso_time = r'''(?P<time>
    (?P<hour>\d{2})
    (
        (?P<min>\d{2})
        (
            (?P<sec>\d{2})
            (?P<sub_sec>\d+)?
        )?
    )?
)
'''


def pattern(*components):
    pattern ='^' + ''.join(components) + '$'
    return re.compile(pattern, re.X)


PATTERNS = {
    'dt_ext': pattern(iso_date_extended, '(T', iso_time_extended, iso_tz_extended, '?)?'),
    'dt': pattern(iso_date, '(T', iso_time, iso_tz, '?)?'),
    'time_ext': pattern('T?', iso_time_extended, iso_tz_extended, '?'),
    'time': pattern('T?', iso_time, iso_tz, '?'),
    'tz': pattern('T?', iso_tz_glob, '?'),
}


class TimeZone(datetime.tzinfo):
    def __init__(self, name):
        params = {}
        if name == 'Z':
            offset = 0
        else:
            matches = PATTERNS['tz'].match(name)
            if matches is None:
                raise ValueError('not an ISO8601 tz')
            m = matches.groupdict()
            direction = m.get('direction', '+')
            if m.get('hour', None):
                params['hours'] = int(direction+m['hour'])
            if m.get('min', None):
                params['minutes'] = int(direction+m['min'])
        self.__offset = datetime.timedelta(**params)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return datetime.timedelta(seconds=0)


STDOFFSET = datetime.timedelta(seconds = -time.timezone)
if time.daylight:
    DSTOFFSET = datetime.timedelta(seconds = -time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET

class LocalTimezone(datetime.tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return datetime.timedelta(seconds=0)

    def tzname(self, dt):
        return time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, 0)
        stamp = time.mktime(tt)
        tt = time.localtime(stamp)
        return tt.tm_isdst > 0

TZ_LOCAL = LocalTimezone()


def parse(date, now=None):
    """
    Returns corresponding datetime.

    date
      any ISO8601 valid value

    now
      datetime reference, almost used for short time value,
      it will setup the date and timezone

    >>> now = datetime.datetime(year=1950, month=2, day=27,
    ...         hour=14, minute=17, second=22, microsecond=110, tzinfo=TZ_LOCAL)
    >>> print parse("1997", now)
    1997-01-01 00:00:00+01:00
    >>> print parse("199707", now)
    1997-07-01 00:00:00+02:00
    >>> print parse("1997-07", now)
    1997-07-01 00:00:00+02:00
    >>> print parse("19970731", now)
    1997-07-31 00:00:00+02:00
    >>> print parse("1997-07-31", now)
    1997-07-31 00:00:00+02:00
    >>> print parse("1997206", now)
    1997-07-25 00:00:00+02:00
    >>> print parse("1997-206", now)
    1997-07-25 00:00:00+02:00
    >>> print parse("2004W453", now)
    2004-11-03 00:00:00+01:00
    >>> print parse("2004-W45-3", now)
    2004-11-03 00:00:00+01:00
    >>> print parse("19970716T1920", now)
    1997-07-16 19:20:00+02:00
    >>> print parse("1997-07-16T19:20", now)
    1997-07-16 19:20:00+02:00
    >>> print parse("19970716T192030", now)
    1997-07-16 19:20:30+02:00
    >>> print parse("1997-07-16T19:20:30", now)
    1997-07-16 19:20:30+02:00
    >>> print parse("19970716T192030423", now)
    1997-07-16 19:20:30.423000+02:00
    >>> print parse("1997-07-16T19:20:30,4", now)
    1997-07-16 19:20:30.400000+02:00
    >>> print parse("19970716T1920+0100", now)
    1997-07-16 19:20:00+01:00
    >>> print parse("1997-07-16T19:20+01:00", now)
    1997-07-16 19:20:00+01:00
    >>> print parse("19970716T192030+0100", now)
    1997-07-16 19:20:30+01:00
    >>> print parse("1997-07-16T19:20:30+01:00", now)
    1997-07-16 19:20:30+01:00
    >>> print parse("T19+0100", now)
    1950-02-27 19:00:00+01:00
    >>> print parse("T19+01:00", now)
    1950-02-27 19:00:00+01:00
    >>> print parse("T1920+0100", now)
    1950-02-27 19:20:00+01:00
    >>> print parse("T19:20+01:00", now)
    1950-02-27 19:20:00+01:00
    >>> print parse("T192030+0100", now)
    1950-02-27 19:20:30+01:00
    >>> print parse("T19:20:30+01:00", now)
    1950-02-27 19:20:30+01:00
    >>> print parse("T1920304+0100", now)
    1950-02-27 19:20:30.400000+01:00
    >>> print parse("T19:20:30,4+01:00", now)
    1950-02-27 19:20:30.400000+01:00
    >>> print parse("T19:20:30Z", now)
    1950-02-27 19:20:30+00:00
    """
    for pattern in PATTERNS.values():
        matches = pattern.match(date)
        if matches:
            break

    if matches is None:
        raise ValueError("Unparsable date {}".format(date))

    if not now:
        now = datetime.datetime.now()

    m = matches.groupdict()

    params = {}
    if m.get('date', None) is None:
        params.update({
            '%Y': now.year,
            '%m': now.month,
            '%d': now.day,
        })

    if m.get('year', None):
        params['%Y'] = m['year']
    if m.get('month', None):
        params['%m'] = m['month']
    if m.get('day', None):
        params['%d'] = m['day']
    if m.get('hour', None):
        params['%H'] = m['hour']
    if m.get('min', None):
        params['%M'] = m['min']
    if m.get('sec', None):
        params['%S'] = m['sec']
    if m.get('day_ord', None):
        params['%j'] = m['day_ord']
    if m.get('week', None):
        params['%W'] = int(m['week']) - 1
    if m.get('week_day', None):
        #          ISO 8601   strptime
        # Monday   1          1
        # Saturday 6          6
        # Sunday   7          0
        week_day = m['week_day']
        if week_day in (7, '7'):
            week_day = 0
        params['%w'] = week_day
    f, s = [], []
    for name, value in params.items():
        f.append(str(name))
        s.append(str(value))

    d = datetime.datetime.strptime(' '.join(s), ' '.join(f))
    display = False
    if m.get('tz', None):
        d = d.replace(
            tzinfo= TimeZone(m['tz'])
        )
    else:
        # no timezone given, use localmachine
        display = True
        d = d.replace(
            tzinfo= TZ_LOCAL
        )

    if m.get('sub_sec', None):
        ms = Decimal('.' + m['sub_sec']) * 1000000
        d = d + datetime.timedelta(microseconds=int(ms))

    return d


if __name__ == '__main__':
    import argparse, sys
    parser = argparse.ArgumentParser(description='Converts into datetime')
    parser.add_argument('dates', type=str, nargs='+',
                       help='dates to be parsed')
    parser.add_argument('-t', '--test', action='store_true', help='run tests')
    args = parser.parse_args()
    if args.test:
        print "run tests"
        import doctest
        doctest.testmod()
        sys.exit()
    if args.dates:
        for date in args.dates:
            try:
                print parse(date)
            except ValueError as e:
                print e.message
        sys.exit()
    parser.print_help()
