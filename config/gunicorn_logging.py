"""Sanitize Gunicorn diagnostics, including startup and worker exceptions."""

import sys

from gunicorn.glogging import Logger

from config.diagnostics import DiagnosticFormatter, SafeStreamHandler


class StructuredLogger(Logger):
    def setup(self, cfg):
        super().setup(cfg)
        for logger in (self.error_log, self.access_log):
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
                handler.close()
        handler = SafeStreamHandler(sys.stdout)
        handler.setFormatter(DiagnosticFormatter("web"))
        self.error_log.addHandler(handler)
