import sys
import traceback
from datetime import datetime

from poptimizer.__main__ import optimize
from poptimizer.__main__ import evolve
from poptimizer import config


def opt(ports_to_optimize, ports_wht_lst):
    try:
        optimize(ports_to_optimize, ports_wht_lst)
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

    ports = set(path.name for path in config.PORT_PATH.glob("*.yaml")) - config.NOT_USED_PORTS - config.WHITE_LIST_PORTS
    all_ports = config.WHITE_LIST_PORTS.union(config.NOT_USED_PORTS)
    for p in ports:
        opt({p}.union(all_ports), config.WHITE_LIST_PORTS)
    opt(ports.union(all_ports), all_ports)
