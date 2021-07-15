# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
import sys
import datetime
import traceback

# ---- Third party imports
from qtpy.QtCore import QObject, Signal
from qtpy.QtWidgets import QApplication


class ExceptHook(QObject):
    """
    A Qt object to catch exceptions and emit a formatted string of the error.
    """
    sig_except_caught = Signal(str)

    def excepthook(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions."""
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        if not issubclass(exc_type, SystemExit):
            log_msg = ''.join(traceback.format_exception(
                exc_type, exc_value, exc_traceback))
            self.sig_except_caught.emit(log_msg)


class StandardStreamEmitter(QObject):
    """
    A Qt object to intercept and emit the input and output of the
    Python interpreter.

    https://docs.python.org/3/library/sys.html#sys.stdout
    https://docs.python.org/3/library/sys.html#sys.stderr
    """
    sig_new_text = Signal(str)

    def write(self, text):
        try:
            sys.__stdout__.write(text)
        except Exception:
            pass
        self.sig_new_text.emit(str(text))


class SysCaptureManager(QObject):
    """
    A manager to capture and manage Python's standard input and output
    streams, logging and internal errors reporting.

    Important Note:
        the system capture manager should NOT be started when testing
        under pytest because this will cause problems with the way
        pytest is already capturing standard system messages and
        raised exceptions.

        See pytest/src/_pytest/capture.py
    """

    def __init__(self, start_capture=False):
        super().__init__()
        self._stdstream_stack = ''
        self._stdstream_consoles = []
        self._is_capturing = False

        # Setup the Except hook.
        self.except_hook = ExceptHook()
        self.except_hook.sig_except_caught.connect(self._handle_except)

        # Setup the standard stream emitter.
        self.stdout_emitter = StandardStreamEmitter()
        self.stdout_emitter.sig_new_text.connect(self.__handle_stdout)

        self.stderr_emitter = StandardStreamEmitter()
        self.stderr_emitter.sig_new_text.connect(self.handle_stderr)

        if start_capture:
            self.start_capture()

    def start_capture(self):
        """
        Start capturing Python interpreter standard messages and unhandled
        raised exceptions.

        Important Note:
            the system capture manager should NOT be started when testing
            under pytest because this will cause problems with the way
            pytest is already capturing standard system messages and
            raised exceptions.

            See pytest/src/_pytest/capture.py
        """
        self._is_capturing = True
        self.__orig_except_hook = sys.excepthook
        self.__orig_stdout = sys.stdout
        self.__orig_stderr = sys.stderr

        sys.excepthook = self.except_hook.excepthook
        sys.stdout = self.stdout_emitter
        sys.stderr = self.stderr_emitter

    def stop_capture(self):
        """
        Stop capturing Python interpreter standard messages and unhandled
        raised exceptions.
        """
        if self._is_capturing:
            self._is_capturing = False
            sys.excepthook = self.__orig_except_hook
            sys.stdout = self.__orig_stdout
            sys.stderr = self.__orig_stderr

    def register_stdstream_console(self, console):
        """
        Register the specified console to this system capture manager.
        """
        self._stdstream_consoles.append(console)
        console.write(self._stdstream_stack)

    def handle_stderr(self, text):
        """
        Handle Python interpreter standard errors.
        """
        self._stdstream_stack += text
        for console in self._stdstream_consoles:
            console.write(text)

    def __handle_stdout(self, text):
        """
        Handle Python interpreter standard output.
        """
        self._stdstream_stack += text
        for console in self._stdstream_consoles:
            console.write(text)

    def _handle_except(self, log_msg):
        """
        Handle raised exceptions that have not been handled properly
        internally and need to be reported for bug fixing.
        """
        from sardes.widgets.dialogs import ExceptDialog
        QApplication.restoreOverrideCursor()
        except_dialog = ExceptDialog(log_msg, self._stdstream_stack)
        except_dialog.exec_()
