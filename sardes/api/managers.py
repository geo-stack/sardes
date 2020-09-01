# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

# ---- Standard imports
from collections import OrderedDict
import os.path as osp
from time import sleep
import uuid

# ---- Third party imports
import pandas as pd
from qtpy.QtCore import QObject, QThread, Signal, Slot


class WorkerBase(QObject):
    """
    A worker to communicate with the project database without blocking the gui.
    """
    sig_task_completed = Signal(object, object)

    def __init__(self):
        super().__init__()
        self.project_accessor = None
        self._tasks = OrderedDict()

    def add_task(self, task_uuid4, task, *args, **kargs):
        """
        Add a task to the stack that will be executed when the thread of
        this worker is started.
        """
        self._tasks[task_uuid4] = (task, args, kargs)

    def run_tasks(self):
        """Execute the tasks that were added to the stack."""
        for task_uuid4, (task, args, kargs) in self._tasks.items():
            method_to_exec = getattr(self, '_' + task)
            returned_values = method_to_exec(*args, **kargs)
            self.sig_task_completed.emit(task_uuid4, returned_values)
        self._tasks = OrderedDict()
        self.thread().quit()

