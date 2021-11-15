import sys
import traceback
from datetime import datetime

from poptimizer.__main__ import optimize
from poptimizer.data.views.listing import last_history_date
from poptimizer.__main__ import evolve
from poptimizer import config


def opt(ports):
    date = last_history_date()
    try:
        optimize(date, ports=ports)
    except Exception as e:
        exc_info = sys.exc_info()
        traceback.print_exception(*exc_info)
        del exc_info


if __name__ == '__main__':
    try:
        print('NOW is', datetime.today())
        evolve()
    except Exception as e:
        exc_info = sys.exc_info()
        traceback.print_exception(*exc_info)
        del exc_info
        print(e)

    ports = set(path.name for path in config.PORT_PATH.glob("*.yaml")) - config.NOT_USED_PORTS - config.BASE_PORTS
    for p in ports:
        opt(config.BASE_PORTS.union({p}))
    opt(config.BASE_PORTS.union(ports))