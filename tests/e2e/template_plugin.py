def template_filter(value):
    return value.upper()


def template_test(value):
    return value == "test"


def template_global():
    return "test"


PLUGIN_FILTERS = {
    "template_filter": template_filter,
}

PLUGIN_TESTS = {
    "template_test": template_test,
}

PLUGIN_GLOBALS = {
    "template_global": template_global,
}
