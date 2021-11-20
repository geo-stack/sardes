# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC
import uuid


class TableEditTypes(Enum):
    """
    An enum that list all types of commands that are used to edit
    the content of SardesTableData, SardesTableModel and SardesTableView
    classes.
    """
    EditValue = 0
    AddRows = 1
    DeleteRows = 2


@dataclass
class TableEdit(ABC):
    """
    A base class for table data, table models, and table views edit commands.

    All edit commands *must* inherit this class and reimplement its interface.

    Attributes
    ----------
    parent : SardesTableData, SardesTableModel or SardesTableView
        A SardesTableData object on which the edit are executed.
    """
    parent: object
    id: uuid.UUID = field(default_factory=uuid.uuid4, init=False)

    def execute(self):
        pass

    def undo(self):
        """Undo this table edit."""
        pass

    def redo(self):
        """Redo this table edit."""
        pass

    @classmethod
    def type(cls):
        """
        Return the type of table edits this edit command corresponds to.

        This make sure unified edit command names and types are used for
        all SardesTableData, SardesTableModel and SardesTableView.
        """
        return getattr(TableEditTypes, cls.__name__)


@dataclass
class TableEditsController(object):
    undo_stack: list[TableEdit] = field(default_factory=list)
    redo_stack: list[TableEdit] = field(default_factory=list)

    def undo_count(self):
        """Return the number of edits in the undo stack."""
        return len(self.undo_stack)

    def redo_count(self):
        """Return the number of edits in the redo stack."""
        return len(self.redo_stack)

    def execute(self, edit: TableEdit):
        """Execute and return the given table edit."""
        edit.execute()
        self.redo_stack.clear()
        self.undo_stack.append(edit)
        return edit

    def undo(self):
        """Undo and return the last edit added to the undo stack."""
        if not self.undo_stack:
            return
        edit = self.undo_stack.pop()
        edit.undo()
        self.redo_stack.append(edit)
        return edit

    def redo(self):
        """Redo and return the last edit added to the undo stack."""
        if not self.redo_stack:
            return
        edit = self.redo_stack.pop()
        edit.redo()
        self.undo_stack.append(edit)
        return edit

    def clear(self):
        """Clear all edits from the undo and redo stacks."""
        self.undo_stack.clear()
        self.redo_stack.clear()
