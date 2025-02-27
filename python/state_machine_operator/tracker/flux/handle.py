import sys

try:
    import flux
except ImportError:
    sys.exit("flux python is required to use the flux tracker")

handle = None


def get_handle():
    global handle
    if handle is None:
        handle = flux.Flux()
    return handle
