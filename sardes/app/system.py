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
        if sys.__stdout__ is not None:
            sys.__stdout__.write(text)
        self.sig_new_text.emit(str(text))


class InternalSystemManager(QObject):
    """
    A manager to manage Python's standard input and output streams, logging
    and internal errors reporting.
    """

    def __init__(self):
        super().__init__()
        self._stdstream_stack = ''
        self._stdstream_consoles = []

        # Setup the Except hook.
        self.except_hook = ExceptHook()
        self.except_hook.sig_except_caught.connect(self._handle_except)
        sys.excepthook = self.except_hook.excepthook

        # Setup the standard stream emitter.
        self.stdout_emitter = StandardStreamEmitter()
        self.stdout_emitter.sig_new_text.connect(self.__handle_stdout)
        sys.stdout = self.stdout_emitter

        self.stderr_emitter = StandardStreamEmitter()
        self.stderr_emitter.sig_new_text.connect(self.handle_stderr)
        sys.stderr = self.stderr_emitter

    def register_stdstream_console(self, console):
        self._stdstream_consoles.append(console)
        console.write(self._stdstream_stack)

    def handle_stderr(self, text):
        self._stdstream_stack += text
        for console in self._stdstream_consoles:
            console.write(text)

    def __handle_stdout(self, text):
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

    def __del__(self):
        """Restore sys standard excepthook and stream."""
        sys.excepthook = sys.__excepthook__
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
