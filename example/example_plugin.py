import getpass
import itertools


def fooify(value):
    return "".join(t[1] for t in zip(value, itertools.cycle("foo")))


def is_root(user):
    return user == "root"


def current_user():
    return getpass.getuser()


PLUGIN_FILTERS = {
    "fooify": fooify,
}

PLUGIN_TESTS = {
    "root": is_root,
}

PLUGIN_GLOBALS = {
    "current_user": current_user,
}
