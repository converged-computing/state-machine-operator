from logging import getLogger

LOGGER = getLogger(__name__)


def convert_walltime_to_seconds(walltime):
    """
    This is from flux and the function could be shared
    """
    # An integer or float was provided
    if isinstance(walltime, int) or isinstance(walltime, float):
        LOGGER.debug("Encountered numeric walltime = %s", str(walltime))
        return int(float(walltime) * 60.0)

    # A string was provided that will convert to numeric
    elif isinstance(walltime, str) and walltime.isnumeric():
        LOGGER.debug("Encountered numeric walltime = %s", str(walltime))
        return int(float(walltime) * 60.0)

    # A string was provided that needs to be parsed
    elif ":" in walltime:
        LOGGER.debug("Converting %s to seconds...", walltime)
        seconds = 0.0
        for i, value in enumerate(walltime.split(":")[::-1]):
            seconds += float(value) * (60.0**i)
        return seconds

    # Don't set a wall time
    elif not walltime or (isinstance(walltime, str) and walltime == "inf"):
        return 0

    # If we get here, we have an error
    msg = f"Walltime value '{walltime}' is not an integer or colon-" f"separated string."
    LOGGER.error(msg)
    raise ValueError(msg)
