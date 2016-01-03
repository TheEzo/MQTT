__author__ = 'tezzo'
import time
from datetime import datetime


def convertTimestampToSQLDateTime(value):
    return time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(value))

def convertSQLDateTimeToTimestamp(value):
    return time.mktime(time.strptime(value, '%Y-%m-%d %H:%M:%S'))

now = datetime.now()

print convertTimestampToSQLDateTime(now)
