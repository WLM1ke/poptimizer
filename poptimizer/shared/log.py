import datetime
import gzip
import os
import shutil
import sys
from logging import Formatter, StreamHandler
from logging.handlers import RotatingFileHandler


class UtcMicrosecondsFormatter(Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.datetime.utcfromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s.%03d" % (t, record.msecs)
        return s


def rotator(source, dest):
    if os.path.exists(source):
        os.rename(source, dest)
        with open(dest, 'rb') as f_in, gzip.open(dest + '.gz', 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(dest)


def namer(default_name):
    name = default_name.split('.')[0]
    return name + '_' + datetime.datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S_%f') + '.log'


def formatter():
    formatter = UtcMicrosecondsFormatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(filename)s | line#%(lineno)d | pid#%(process)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S.%f'
    )
    return formatter


def get_handlers():
    logs_path = 'logs'
    os.makedirs(logs_path, exist_ok=True)
    file_handler = RotatingFileHandler(filename=logs_path+'/log.log',
                                       encoding='utf-8',
                                       maxBytes=2 * 1024 ** 2,
                                       backupCount=1,
                                       delay=False
                                       )
    file_handler.rotator = rotator
    file_handler.namer = namer
    file_handler.setFormatter(formatter())

    stream_handler = StreamHandler(sys.stdout)
    stream_handler.setFormatter(Formatter('%(message)s'))
    return [file_handler, stream_handler]
