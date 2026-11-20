"""Entry-point context; auxiliary commands must not own a service log file."""

management_command = None


def file_logging_enabled():
    return management_command in (None, "runserver", "run_worker")
