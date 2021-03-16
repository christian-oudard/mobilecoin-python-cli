from decimal import Decimal


TRANSACTION_FEE = Decimal('0.01')


PMOB = Decimal('1e12')


def mob2pmob(x):
    """ Convert from MOB to picoMOB. """
    return round(Decimal(x) * PMOB)


def pmob2mob(x):
    """ Convert from picoMOB to MOB. """
    return int(x) / PMOB


def try_int(x):
    if x is not None:
        return int(x)
