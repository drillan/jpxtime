import cPickle as pickle
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from dateutil.parser import parse
from dateutil.relativedelta import FR
from dateutil.relativedelta import relativedelta
from itertools import product
import os
import urllib2
import yaml

'''memo
http://www.jpx.co.jp/english/derivatives/rules/trading-hours/index.html
'''

datadir = os.path.dirname(os.path.abspath(__file__))
cachedays = 365
ONE_YEAR_TO_SECONDS_365 = 31536000
ONE_YEAR_TO_SECONDS_245 = 21168000
ONE_DAY_TO_SECONDS = 86400


class DaySession(object):

    def __init__(self, dt):
        if dt >= datetime(2016, 7, 19):
            self.opening = time(8, 45)
            self.pre_closing = time(15, 10)
            self.closing = time(15, 15)
        else:
            self.opening = time(9, 0)
            self.pre_closing = time(15, 10)
            self.closing = time(15, 15)


class NightSession(object):

    def __init__(self, dt):
        if dt >= datetime(2016, 7, 19):
            self.opening = time(16, 30)
            self.pre_closing = time(5, 25)
            self.closing = time(5, 30)
        else:
            self.opening = time(16, 30)
            self.pre_closing = time(2, 55)
            self.closing = time(3, 0)


class Session(object):

    def __init__(self, dt):
        self.dt = dt
        d = DaySession(dt)
        n = NightSession(dt)
        t = dt.time()
        if time(0, 0) <= t <= n.pre_closing:
            id = 0
        if n.pre_closing <= t <= n.closing:
            id = 1
        if n.closing < t < d.opening:
            id = 2
        if d.opening <= t <= d.pre_closing:
            id = 3
        if d.pre_closing <= t <= d.closing:
            id = 4
        if d.closing < t < n.opening:
            id = 5
        if n.opening <= t:
            id = 6
        self.session = {0: 'Regular_Session(NS)', 1: 'Closing_Auction(NS)',
                     2: 'Closed', 3: 'Regular_Session(DS)',
                     4: 'Closing_Auction(DS)',
                     5: 'Closed', 6: 'Regular_Session(NS)'}
        self.open_flag = {0: 1, 1: 2, 2: 0, 3: 1, 4: 2, 5: 0, 6: 1}
        self.session_id = id
        self.session_name = self.session[self.session_id]
        self.is_open = self._is_workingday() * self.open_flag[self.session_id]
        if not self.is_open:
            self.session_name = 'Closed'

    def _is_workingday(self):
        d = self.dt.date()
        h = JpxHoliday()
        if self.session_id < 2:
            d = d - timedelta(days=1)
        return not h.is_holiday(d)


class SqData(object):

    def get_sq_date(self, year, month):
        sq_date = date(year, month, 1) + relativedelta(weekday=FR(2))
        h = JpxHoliday()
        if h.is_holiday(sq_date):
            for i in xrange(14):
                sq_date = sq_date - timedelta(days=1)
                if h.is_holiday(sq_date):
                    continue
                else:
                    break
        return sq_date

    def create_data(self):
        START_YEAR = 1988
        END_YEAR = 2050
        period = product(xrange(START_YEAR, END_YEAR + 1), xrange(1, 13))
        data = dict(map(lambda x: (x, self.get_sq_date(*x)), period))
        return data


class Cache(object):

    def __init__(self, cachefile):
        self.cachefile = cachefile

    def get(self):
        file = os.path.join(os.path.expanduser(datadir), self.cachefile)
        if not os.path.exists(file):
            return None
        today = date.today()
        with open(file) as f:
            dat = pickle.load(f)
        if dat['expires'] <= today:
            return None
        else:
            return dat['val']

    def set(self, val):
        expires = date.today() + timedelta(cachedays)
        dat = {'expires': expires, 'val': val}
        file = os.path.join(os.path.expanduser(datadir), self.cachefile)
        with open(file, 'w') as f:
            pickle.dump(dat, f)


class LoadData(object):

    def __init__(self, cachefile, dataname):
        self.__cache = Cache(cachefile)
        self.__dataname = dataname

        self.__c = self.__cache.get()
        if self.__c:
            self._dat = self.__c[self.__dataname]
        else:
            self._dat = self._load_data(self.__cache, self.__dataname)
            self.__cache.set({self.__dataname: self._dat})

    def _load_data(self, cache, dataname):
        pass


class SqDate(LoadData):

    def __init__(self):
        cachefile, dataname = 'sq_cache', 'sq_date'
        LoadData.__init__(self, cachefile, dataname)
        self.sq_date = self._dat

    def _load_data(self, cache, dataname):
        sq_data = SqData()
        return sq_data.create_data()

    def _to_tuple(self, data):
        data_type = type(data)

        def _tuple(data):
            return data

        def _list_set(data):
            return tuple(data)

        def _str(data):
            if len(data) == 4:
                data = '20' + data + '01'
            elif len(data) == 6:
                if data[:2] == '20':
                    data = data + '01'
                else:
                    data = '20' + data
            dt = parse(data)
            return dt.date().timetuple()[:2]

        def _unicode(data):
            return _str(str(data))

        def _int(data):
            return _str(str(data))

        def _datetime(data):
            return data.date().timetuple()[:2]

        def _date(data):
            return data.timetuple()[:2]

        func_dict = {tuple: _tuple, list: _list_set, set: _list_set,
                str: _str, unicode: _unicode, int: _int,
                datetime: _datetime, date: _date}
        return func_dict[data_type](data)

    def get_sq(self, data):
        if len(data) > 1:
            return self.sq_date[data[:2]]
        else:
            return self.sq_date[self._to_tuple(data[0])]

    def get_t(self, t0, t1, year=0):
        if type(t1) == date:
            t1_date = t1
            t1 = datetime.combine(t1, time(9, 0))
        else:
            t1_date = t1.date()
        t0_date = t0.date()
        t = t1 - t0
        if year:
            days = (t1_date - t0_date).days
            holiday = len(filter(jpx_holiday.is_holiday, [
                          t0_date + timedelta(days=x) for x in xrange(days)]))
            t = (t.total_seconds() - holiday * ONE_DAY_TO_SECONDS) / \
                ONE_YEAR_TO_SECONDS_245
        else:
            t = t.total_seconds() / ONE_YEAR_TO_SECONDS_365
        return t


class JpHoliday(LoadData):

    def __init__(self):
        cachefile, dataname = 'holiday_cache', 'holiday_jp'
        LoadData.__init__(self, cachefile, dataname)
        self.holiday_jp = self._dat

    def _load_data(self, cache, dataname):
        URL = 'https://raw.githubusercontent.com/k1LoW/holiday_jp/master/holidays.yml'
        res = urllib2.urlopen(URL)
        return yaml.load(res)

    def is_calendar_holiday(self, dt):
        SATURDAY = 5
        SUNDAY = 6
        w = dt.weekday()
        if w == SATURDAY or w == SUNDAY:
            return True
        elif dt in self.holiday_jp.keys():
            return True
        else:
            return False


class JpxHoliday(JpHoliday):

    def is_holiday(self, dt):
        jpx_holidays = ((1, 2), (1, 3), (12, 31))
        ym = dt.timetuple()[1:3]
        if self.is_calendar_holiday(dt) or ym in jpx_holidays:
            return True
        else:
            return False


jpx_holiday = JpxHoliday()
sq = SqDate()


def is_open(dt):
    s = Session(dt)
    return s.is_open


def get_sq(*data):
    return sq.get_sq(data)


def get_t(t0, t1, year=0):
    return sq.get_t(t0, t1, year)


if __name__ == "__main__":
    pass
