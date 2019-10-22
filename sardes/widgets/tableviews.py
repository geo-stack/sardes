# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Standard imports
import sys
from collections import OrderedDict
from datetime import datetime
import itertools
from math import floor, ceil

# ---- Third party imports
import pandas as pd
from qtpy.QtCore import (QAbstractTableModel, QEvent, QModelIndex,
                         QSortFilterProxyModel, Qt, QVariant, Signal, Slot,
                         QItemSelection, QItemSelectionModel, QRect,
                         )
from qtpy.QtGui import QColor, QCursor, QPen
from qtpy.QtWidgets import (QApplication, QComboBox, QDateEdit, QDateTimeEdit,
                            QDoubleSpinBox, QHeaderView, QLabel, QLineEdit,
                            QMenu, QMessageBox, QSpinBox, QStyledItemDelegate,
                            QTableView, QTextEdit, QListView, QStyle,
                            QStyleOption)

# ---- Local imports
from sardes import __appname__
from sardes.api.panes import SardesPaneWidget
from sardes.config.locale import _
from sardes.config.gui import get_iconsize
from sardes.utils.data_operations import intervals_extract
from sardes.utils.qthelpers import (
    create_action, create_toolbutton, create_toolbar_stretcher,
    qbytearray_to_hexstate, hexstate_to_qbytearray, qdatetime_from_datetime,
    get_datetime_from_editor)


# =============================================================================
# ---- Delegates
# =============================================================================
class SardesItemDelegateBase(QStyledItemDelegate):
    """
    Basic functionality for Sardes item delegates.

    WARNING: Don't override any methods or attributes present here.
    """

    def __init__(self, model_view, unique_constraint=False,
                 is_required=False):
        super() .__init__(parent=model_view)
        self.model_view = model_view
        self.model_index = None
        self.editor = None
        self.unique_constraint = unique_constraint
        self.is_required = is_required

    # ---- Qt methods override
    def createEditor(self, parent, option, model_index):
        """Qt method override."""
        self.model_index = model_index
        self.editor = self.create_editor(parent)
        self.editor.installEventFilter(self)
        return self.editor

    def setEditorData(self, editor, index):
        """Qt method override."""
        self.set_editor_data(self.get_model_data())

    def setModelData(self, editor, model, index):
        """Qt method override."""
        pass

    def paint(self, painter, option, index):
        """
        Override Qt method to paint a custom focus rectangle and to force the
        table to get the style from QListView, which looks more modern.
        """
        widget = QListView()
        style = widget.style()

        # We remove the State_HasFocus from the option so that Qt doesn't
        # paint it. We paint our own focus rectangle instead.
        has_focus = bool(option.state & QStyle.State_HasFocus)
        option.state &= ~ QStyle.State_HasFocus

        # We dont want cells to be highlighted because of mouse over.
        option.state &= ~QStyle.State_MouseOver

        # We must set the text ouselves or else no text is painted.
        option.text = index.data()

        # We must fill the background with a solid color before painting the
        # control. This is necessary, for example, to color the background of
        # the cells with un-saved edits.
        painter.fillRect(option.rect, index.data(Qt.BackgroundRole))
        style.drawControl(QStyle.CE_ItemViewItem, option, painter, widget)

        # Finally, we paint a focus rectangle ourselves.
        if has_focus:
            painter.save()
            w = 2
            pen = QPen(Qt.black, w, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
            painter.setPen(pen)
            painter.drawRect(option.rect.adjusted(
                floor(w / 2), floor(w / 2), -ceil(w / 2), -ceil(w / 2)))
            painter.restore()

    # ---- Private methods
    def eventFilter(self, widget, event):
        """
        An event filter to control when the data of this delegate's editor
        are commited to the model.
        """
        if self.editor and event.type() == QEvent.KeyPress:
            """Commit edits on Enter of Ctrl+Enter key press."""
            key_cond = event.key() in (Qt.Key_Return, Qt.Key_Enter)
            mod_cond = (not event.modifiers() or
                        event.modifiers() & Qt.ControlModifier)
            if key_cond and mod_cond:
                self.commit_data()
                return True
        return super().eventFilter(widget, event)

    def commit_data(self):
        """
        Commit the data of this delegate's editor to the model.
        """
        self.closeEditor.emit(self.editor, self.NoHint)
        editor_value = self.get_editor_data()
        model_value = self.get_model_data()
        if editor_value != model_value:
            # We need to validate the edits before submitting the edits to
            # the model or else, unique check will always return an error.
            error_message = self.validate_edits()

            # We store the edits even if the validation fails, so that
            # when we return to this delegate to edits, the last value
            # entered by the user is preserved.
            self.model().set_data_edits_at(self.model_index, editor_value)
            if error_message is not None:
                self.model_view.raise_edits_error(
                    self.model_index, error_message)

    # ---- Public methods
    def model(self):
        """
        Return the model whose data this item delegate is used to edit.
        """
        return self.model_index.model()

    def get_model_data(self):
        """
        Return the value stored in the model at the model index
        corresponding to this item delegate.
        """
        return self.model_index.model().get_value_at(self.model_index)

    def validate_unique_constaint(self):
        """
        If a unique constraint is set for this item delegate, check that
        the edited value does not violate that and return an error message
        if it does.
        """
        field_name = self.model().get_horizontal_header_label_at(
            self.model_index.column())
        edited_value = self.get_editor_data()
        if (self.unique_constraint and self.model().is_value_in_column(
                self.model_index, edited_value)):
            return _(
                "<b>Duplicate key value violates unique constraint.</b>"
                "<br><br>"
                "The {} <i>{}</i> already exists. Please use another value"
                ).format(field_name, edited_value, field_name)
        else:
            return None

    def clear_model_data(self, model_index):
        """
        Set the data of the model index associated with this delegate to
        a null value.

        Note that we need to pass the model index as an argument, else
        it won't be possible to clear the data if the editor have not been
        created at least once.
        """
        if not self.is_required:
            model_index.model().set_data_edits_at(model_index, None)


class NotEditableDelegate(SardesItemDelegateBase):
    """
    A delegate used to indicate that the items in the associated
    column are not editable.
    """

    def __init__(self, model_view):
        super().__init__(model_view, is_required=True)

    def createEditor(self, *args, **kargs):
        return None

    def setEditorData(self, editor, index):
        pass

    def setModelData(self, editor, model, index):
        pass

    def clear_model_data(self, model_index):
        """
        Override base class method to prevent clearing the model data.
        a null value.
        """
        pass


class SardesItemDelegate(SardesItemDelegateBase):
    """
    Sardes item delegates to edit the data of displayed in a table view.

    Specific delegates *can* inherit this class and reimplement its interface.
    """

    def create_editor(self, parent):
        """Return the editor to use in this item delegate."""
        raise NotImplementedError

    def get_editor_data(self):
        """
        Return the value of this item delegate's editor.

        You may need to reimplement this method if the type of your
        item delegate's editor is not supported or else a NotImplementedError
        will be raised.
        """
        if isinstance(self.editor, QLineEdit):
            data = self.editor.text()
            return None if data == '' else data
        if isinstance(self.editor, QTextEdit):
            data = self.editor.toPlainText()
            return None if data == '' else data
        elif isinstance(self.editor, (QSpinBox, QDoubleSpinBox)):
            return self.editor.value()
        elif isinstance(self.editor, QComboBox):
            return self.editor.itemData(self.editor.currentIndex())
        elif isinstance(self.editor, (QDateEdit, QDateTimeEdit)):
            return get_datetime_from_editor(self.editor)
        else:
            raise NotImplementedError

    def set_editor_data(self, data):
        """
        Set the data of this item delegate's editor.

        You may need to reimplement this method if the type of your
        item delegate's editor is not supported or else a NotImplementedError
        will be raised.
        """
        if isinstance(self.editor, (QTextEdit, QLineEdit)):
            data = '' if (pd.isna(data) or data is None) else data
            self.editor.setText(data)
        elif isinstance(self.editor, (QSpinBox, QDoubleSpinBox)):
            self.editor.setValue(data)
        elif isinstance(self.editor, QComboBox):
            for i in range(self.editor.count()):
                if self.editor.itemData(i) == data:
                    self.editor.setCurrentIndex(i)
                    break
            else:
                self.editor.setCurrentIndex(0)
        elif isinstance(self.editor, (QDateEdit, QDateTimeEdit)):
            data = (datetime.today() if (pd.isna(data) or data is None)
                    else data)
            self.editor.setDateTime(qdatetime_from_datetime(data))
        else:
            raise NotImplementedError

    def validate_edits(self):
        """Validate the value of this item delegate's editor."""
        return None


class DateEditDelegate(SardesItemDelegate):
    """
    A delegate to edit a date.
    """

    def create_editor(self, parent):
        editor = QDateEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("yyyy-MM-dd")
        return editor


class DateTimeDelegate(SardesItemDelegate):
    """
    A delegate to edit a datetime.
    """

    def __init__(self, model_view, display_format=None):
        super() .__init__(model_view)
        self.display_format = ("yyyy-MM-dd hh:mm:ss" if display_format is None
                               else display_format)

    def create_editor(self, parent):
        editor = QDateTimeEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat(self.display_format)
        return editor


class TextEditDelegate(SardesItemDelegate):
    """
    A delegate to edit very long strings that can span over multiple lines.
    """

    def create_editor(self, parent):
        return QTextEdit(parent)


class StringEditDelegate(SardesItemDelegate):
    """
    A delegate to edit a 250 characters strings.
    """
    MAX_LENGTH = 250

    def create_editor(self, parent):
        editor = QLineEdit(parent)
        editor.setMaxLength(self.MAX_LENGTH)
        return editor

    def validate_edits(self):
        return self.validate_unique_constaint()


class NumEditDelegate(SardesItemDelegate):
    """
    A delegate to edit a float or an integer value in a spin box.
    """

    def __init__(self, model_view, decimals=0, bottom=None, top=None,
                 unique_constraint=False):
        super() .__init__(model_view, unique_constraint=unique_constraint)
        self._bottom = bottom
        self._top = top
        self._decimals = decimals

    def create_editor(self, parent):
        if self._decimals == 0:
            editor = QSpinBox(parent)
        else:
            editor = QDoubleSpinBox(parent)
            editor.setDecimals(self._decimals)
        if self._bottom is not None:
            editor.setMinimum(self._bottom)
        if self._top is not None:
            editor.setMaximum(self._top)
        return editor


class BoolEditDelegate(SardesItemDelegate):
    """
    A delegate to edit a boolean value with a combobox.
    """

    def create_editor(self, parent):
        editor = QComboBox(parent)
        editor.addItem(_('Yes'), userData=True)
        editor.addItem(_('No'), userData=False)
        return editor


# =============================================================================
# ---- Table Model
# =============================================================================
class NoDataEdit(object):
    """
    A class to indicate that no edit have been done to the data since last
    save.
    """

    def __init__(self, index, column):
        super() .__init__()
        self.index = index
        self.column = column


class ValueChanged(object):
    """
    A class that represent a change of a value at a given model index.
    """

    def __init__(self, index, column, value, edited_value):
        super() .__init__()
        self.index = index
        self.column = column
        self.value = value
        self.edited_value = edited_value

    def type(self):
        """
        Return an integer that indicates the type of data edit this
        edit correspond to, as defined in :class:`SardesTableModelBase`.
        """
        return SardesTableModelBase.ValueChanged


class SardesTableModelBase(QAbstractTableModel):
    """
    Basic functionality for Sardes table models.

    WARNING: Don't override any methods or attributes present here.
    """
    sig_data_edited = Signal(bool)

    ValueChanged = 0
    RowAdded = 1
    RowRemoved = 2

    def __init__(self, db_connection_manager=None):
        super().__init__()
        self._data_columns_mapper = OrderedDict(self.__data_columns_mapper__)

        # A pandas dataframe containing the data that are shown in the
        # database.
        self.dataf = pd.DataFrame([])
        self.visual_dataf = pd.DataFrame([], columns=self.columns)

        # A list containing the edits made by the user to the
        # content of this table's model data in chronological order.
        self._data_edit_stack = []
        self._new_rows = []
        self._deleted_rows = []

        # A pandas dataframe that contains the edited values at their
        # corresponding data index and column.
        self._edited_dataf = pd.DataFrame(
            [], columns=['index', 'column', 'edited_value'])
        self._edited_dataf.set_index('index', inplace=True, drop=True)
        self._edited_dataf.set_index(
            'column', inplace=True, drop=True, append=True)

        # Sorting and filtering.
        self._sort_by_columns = None
        self._sort_order = Qt.AscendingOrder

        self.set_database_connection_manager(db_connection_manager)

    def set_database_connection_manager(self, db_connection_manager):
        """Setup the database connection manager for this table model."""
        self.db_connection_manager = db_connection_manager
        if db_connection_manager is not None:
            self.db_connection_manager.sig_database_connection_changed.connect(
                self.fetch_model_data)
            self.db_connection_manager.sig_database_data_changed.connect(
                self.fetch_model_data)

    # ---- Columns
    @property
    def columns(self):
        """
        Return the list of keys used to reference the columns in this
        model's data.
        """
        return list(self._data_columns_mapper.keys())

    def columnCount(self, parent=QModelIndex()):
        """Qt method override. Return the number of column of the table."""
        return len(self.columns)

    # ---- Horizontal Headers
    @property
    def horizontal_header_labels(self):
        """
        Return the list of labels that need to be displayed for each column
        of the table's horizontal header.
        """
        return list(self._data_columns_mapper.values())

    def get_horizontal_header_label_at(self, column_or_index):
        """
        Return the text of the label to display in the horizontal
        header for the key or logical index associated
        with the column.
        """
        return self._data_columns_mapper[
            column_or_index if isinstance(column_or_index, str) else
            self.columns[column_or_index]
            ]

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Qt method override."""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.get_horizontal_header_label_at(section)
        if role == Qt.DisplayRole and orientation == Qt.Vertical:
            return section + 1
        else:
            return QVariant()

    # ---- Table data
    def set_model_data(self, dataf):
        """
        Set the content of this table model to the data contained in dataf.

        Parameters
        ----------
        dataf: :class:`pd.DataFrame`
            A pandas dataframe containing the data of this table model. The
            column labels of the dataframe must match the values that are
            mapped in HORIZONTAL_HEADER_LABELS.
        """
        self.dataf = dataf
        self._edited_dataf.drop(self._edited_dataf.index, inplace=True)
        self._data_edit_stack = []
        self._new_rows = []
        self._deleted_rows = []
        self._update_visual_data()

        self.modelReset.emit()
        self.sig_data_edited.emit(False)

    def rowCount(self, parent=QModelIndex()):
        """Qt method override. Return the number visible rows in the table."""
        return len(self.visual_dataf)

    def data(self, index, role=Qt.DisplayRole):
        """Qt method override."""
        if role in [Qt.DisplayRole, Qt.ToolTipRole]:
            return self.visual_dataf.loc[
                self.dataf_index_at(index), self.dataf_column_at(index)]
        elif role == Qt.ForegroundRole:
            return QVariant()
        elif role == Qt.BackgroundRole:
            if self.is_data_edited_at(index):
                return QColor('#CCFF99')
            else:
                return QStyleOption().palette.base().color()
        else:
            return QVariant()

    def flags(self, model_index):
        """Qt method override."""
        return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable

    def get_dataf_value_at(self, model_index):
        """
        Return the unedited value of the model's data at the specified model
        index.
        """
        try:
            return self.dataf.loc[self.dataf_index_at(model_index),
                                  self.dataf_column_at(model_index)]
        except KeyError:
            return None

    def get_value_at(self, model_index):
        """
        Return the edited, visible, value of the model's data at the
        specified model index.
        """
        # We check first if the data was edited by the user if 'ignore_edits'
        # is True.
        value = self.get_edited_data_at(model_index)
        if isinstance(value, NoDataEdit):
            # This means that the value was not edited by the user, so we
            # fetch the value directly from the model's data.
            value = self.get_dataf_value_at(model_index)
        return value

    def is_value_in_column(self, model_index, value):
        """
        Check if the specified value is in the data of this model at the
        column specified by the model index.
        """
        dataf_column = self.dataf_column_at(model_index)

        # First we check if value is found in the edited data.
        if any(self._edited_dataf
               .loc[(slice(None), slice(dataf_column)), 'edited_value']
               .isin([value])):
            return True
        else:
            # Else we check if the value is found in the unedited data
            # of this model's data.
            isin_indexes = self.dataf[self.dataf[dataf_column].isin([value])]
            return any([
                not self.is_data_edited_at(self.index(
                    self.dataf.index.get_loc(index), model_index.column()))
                for index in isin_indexes.index
                ])

    # ---- Visual Data
    def dataf_index_at(self, model_index):
        """
        Return the dataframe index corresponding to the specified visual
        model index.
        """
        return self.visual_dataf.index[model_index.row()]

    def dataf_column_at(self, model_index):
        """
        Return the dataframe column corresponding to the specified visual
        model index.
        """
        return self.columns[model_index.column()]

    def _update_visual_data(self):
        """
        Update the visual dataframe that is used to display the value in
        this tables.
        """
        self.visual_dataf = self.dataf.copy()

        # Fist we apply the edited values to the dataframe.
        for index, column in self._edited_dataf.index:
            self.visual_dataf.loc[index, column] = (
                self._edited_dataf.loc[(index, column), 'edited_value'])

        # Add missing columns to the visual dataframe.
        for column in self.columns:
            if column not in self.visual_dataf.columns:
                self.visual_dataf[column] = ''

        if not self.dataf.empty:
            self.visual_dataf = self.logical_to_visual_data(self.visual_dataf)
            self._filter_visual_data()
            self._sort_visual_data()

            # Transform the data to string and replace nan and boolean
            # values with strings.
            # Note that this must be done after the filtering and sorting
            # is applied or else, it won't work as expected for numerical
            # values.
            self.visual_dataf.fillna(value='', inplace=True)
            self.visual_dataf = self.visual_dataf.astype(str)
            self.visual_dataf.replace(
                to_replace={'True': _('Yes'), 'False': _('No')}, inplace=True)

        self.dataChanged.emit(QModelIndex(), QModelIndex())

    def _filter_visual_data(self):
        """
        Apply the filters to the visual data.
        """
        pass

    def _sort_visual_data(self):
        """
        Sort the visual data.
        """
        if self._sort_by_columns is not None:
            self.visual_dataf.sort_values(
                by=self._sort_by_columns,
                ascending=(self._sort_order == Qt.AscendingOrder),
                inplace=True)

    def sort(self, column, order=Qt.AscendingOrder):
        """
        Implement Qt sort method so that sorting by columns is done with pandas
        instead of using  QSortFilterProxyModel, which is very slow for large
        datasets.

        https://bugreports.qt.io/browse/QTBUG-45208
        https://stackoverflow.com/a/42039683/4481445
        """
        self.layoutAboutToBeChanged.emit()
        old_model_indexes = self.persistentIndexList()
        old_ids = self.visual_dataf.index.copy()

        self._sort_by_columns = None if column == -1 else self.columns[column]
        self._sort_order = order
        self._update_visual_data()

        # Updating persistent indexes
        new_model_indexes = []
        for index in old_model_indexes:
            new_row = self.visual_dataf.index.get_loc(old_ids[index.row()])
            new_model_indexes.append(
                self.index(new_row, index.column(), index.parent()))

        self.changePersistentIndexList(old_model_indexes, new_model_indexes)
        self.layoutChanged.emit()
        self.dataChanged.emit(QModelIndex(), QModelIndex())

    # ---- Data edits
    def data_edit_count(self):
        """
        Return the number of edits in the stack.
        """
        return len(self._data_edit_stack)

    def has_unsaved_data_edits(self):
        """
        Return whether any edits were made to the table's data since last save.
        """
        return bool(len(self._edited_dataf))

    def is_data_edited_at(self, model_index):
        """
        Return whether edits were made at the specified model index
        since last save.
        """
        return (self.dataf_index_at(model_index),
                self.columns[model_index.column()]
                ) in self._edited_dataf.index

    def cancel_all_data_edits(self):
        """
        Cancel all the edits that were made to the table data since last save.
        """
        self._data_edit_stack = []
        self._edited_dataf.drop(self._edited_dataf.index, inplace=True)
        self._update_visual_data()
        self.dataChanged.emit(QModelIndex(), QModelIndex())
        self.sig_data_edited.emit(False)

    def get_edited_data_at(self, model_index):
        """
        Return the edited value, if any, that was made at the specified
        model index since last save.
        """
        dataf_index = self.dataf_index_at(model_index)
        dataf_column = self.dataf_column_at(model_index)
        try:
            return self._edited_dataf.loc[
                (dataf_index, dataf_column), 'edited_value']
        except KeyError:
            return NoDataEdit(dataf_index, dataf_column)

    def set_data_edits_at(self, model_indexes, edited_values):
        """
        Store the values that were edited at the specified model indexes.
        A signal is also emitted to indicate that the data were edited,
        so that the GUI can be updated accordingly.
        """
        if not isinstance(model_indexes, list):
            model_indexes = [model_indexes, ]
        if not isinstance(edited_values, list):
            edited_values = [edited_values, ]

        edits = []
        for model_index, edited_value in zip(model_indexes, edited_values):
            dataf_value = self.get_dataf_value_at(model_index)
            dataf_index = self.dataf_index_at(model_index)
            dataf_column = self.dataf_column_at(model_index)
            edits.append(ValueChanged(
                dataf_index, dataf_column, dataf_value, edited_value))

            # We add the model index to the list of indexes whose value have
            # been edited if the edited value differ from the value saved in
            # the model's data.
            if (dataf_index, dataf_column) in self._edited_dataf.index:
                self._edited_dataf.drop(
                    (dataf_index, dataf_column), inplace=True)
            if dataf_value != edited_value:
                self._edited_dataf.loc[(dataf_index, dataf_column),
                                       'edited_value'
                                       ] = edited_value
        # We store the edited values until it is commited and
        # saved to the database.
        self._data_edit_stack.append(edits)

        # We make the appropriate calls to update the model and GUI.
        self._update_visual_data()
        self.dataChanged.emit(QModelIndex(), QModelIndex())
        self.sig_data_edited.emit(self.has_unsaved_data_edits())

    def undo_last_data_edit(self):
        """
        Undo the last data edits that was added to the stack.
        An update of the view is forced if  update_model_view is True.
        """
        if len(self._data_edit_stack) == 0:
            return

        # Undo the last edits. Note that the last edits can comprise
        # more than one edit.
        last_edits = self._data_edit_stack.pop(-1)
        for last_edit in last_edits:
            if (last_edit.index, last_edit.column) in self._edited_dataf.index:
                self._edited_dataf.drop((last_edit.index, last_edit.column),
                                        inplace=True)

            # Check if there was a previous edit for this model index
            # in the stack and add it to the list of edited data if that is
            # the case.
            for edits in reversed(self._data_edit_stack):
                try:
                    edit = edits[[(edit.index, edit.column) for edit in edits]
                                 .index((last_edit.index, last_edit.column))]
                    self._edited_dataf.loc[
                        (edit.index, edit.column), 'edited_value'
                        ] = edit.edited_value
                except ValueError:
                    continue
                else:
                    break

        self._update_visual_data()
        self.dataChanged.emit(QModelIndex(), QModelIndex())
        self.sig_data_edited.emit(self.has_unsaved_data_edits())


class SardesTableModel(SardesTableModelBase):
    """
    An abstract table model to be used in a table view to display the data
    that are saved in the database.

    All table *must* inherit this class and reimplement its interface.

    """
    # A list of tuple that maps the keys of the columns dataframe with their
    # corresponding human readable label to use in the GUI.
    __data_columns_mapper__ = []

    # The label that will be used to reference this table in the GUI.
    TABLE_TITLE = ''

    # A unique ID that will be used to reference this table in the code and
    # in the user configurations.
    TABLE_ID = ''

    def __init__(self, db_connection_manager=None):
        super().__init__(db_connection_manager)

    def fetch_model_data(self, *args, **kargs):
        """
        Fetch the data for this table model.

        Note that the data need to be passed to :func:`set_model_data`.
        """
        raise NotImplementedError

    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        raise NotImplementedError

    # ---- Visua data
    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.

        Do any transformations to the source data so that they are displayed
        as you want in the table. Note that these transformations are
        applied to the visual dataframe, so that the source data are
        preserved in the process.

        For example, if you would like to display boolean values in a given
        column of the table as 'Yes' or 'No' strings, you would need to do:

        visual_dataf[column].replace(
            to_replace={True: 'Yes', False: 'No'}, inplace=False)
        """
        return visual_dataf

    # ---- Data edits
    def save_data_edits(self):
        """
        Save all data edits to the database.
        """
        raise NotImplementedError


# =============================================================================
# ---- Table View
# =============================================================================
class SardesHeaderView(QHeaderView):
    """
    An horizontal header view that allow sorting by columns on double mouse
    click events (instead of single mouse clicks) and allow to clear the
    sorting of it's associated table view.
    """

    def __init__(self, parent, orientation=Qt.Horizontal):
        super().__init__(orientation, parent)
        self.setHighlightSections(True)
        self.setSectionsClickable(True)
        self.setSectionsMovable(True)
        self.sectionDoubleClicked.connect(self._handle_section_doubleclick)

        # Sort indicators variables to allow sorting on mouse double click
        # events instead of single click events.
        self._sort_indicator_section = -1
        self._sort_indicator_order = Qt.AscendingOrder
        self._update_sort_indicator()
        self.sortIndicatorChanged.connect(self._update_sort_indicator)

    def clear_sort(self):
        """
        Clear all sorts applied to the columns of the tabl associated with this
        header view.
        """
        self._sort_indicator_section = -1
        self._sort_indicator_order = 0
        self.setSortIndicatorShown(False)
        self._update_sort_indicator()
        self.parent().model().sort(-1)

    def sort_by_column(self, section, order):
        """
        Sort the rows of the table associated with this header view
        by ordering the data of the specified section (column) in the
        specified sorting order.
        """
        self._sort_indicator_section = section
        self._sort_indicator_order = order
        self._update_sort_indicator()
        self.setSortIndicatorShown(True)
        self.parent().sortByColumn(section, order)

    # ---- Utils
    def visual_rect_at(self, section):
        """
        Return the visual rect of for the specified section.
        """
        return QRect(self.sectionViewportPosition(section), 0,
                     self.sectionSize(section), self.size().height())

    # ---- Private methods
    @Slot(int)
    def _handle_section_doubleclick(self, section):
        """
        Sort data on the column that was double clicked with the mouse.
        """
        order = (Qt.AscendingOrder if
                 section != self._sort_indicator_section else
                 int(not bool(self._sort_indicator_order)))
        self.sort_by_column(section, order)

    def _update_sort_indicator(self):
        """
        Force the sort indicator section and order to override Qt behaviour
        on single mouse click.
        """
        self.blockSignals(True)
        self.setSortIndicator(
            self._sort_indicator_section, self._sort_indicator_order)
        self.blockSignals(False)


class SardesTableView(QTableView):
    """
    Sardes table view class to display and edit the data that are
    saved in the database.
    """
    sig_data_edited = Signal(bool)

    def __init__(self, table_model, parent=None):
        super().__init__(parent)
        self.setSortingEnabled(False)
        self.setAlternatingRowColors(False)
        self.setCornerButtonEnabled(True)
        self.setHorizontalHeader(SardesHeaderView(parent=self))
        self.setEditTriggers(self.DoubleClicked)
        self.setMouseTracking(True)

        self._actions = {}
        self._setup_table_model(table_model)
        self._setup_item_delegates()
        self._setup_shortcuts()

        # List of QAction to toggle the visibility this table's columns.
        self._setup_column_visibility_actions()

    def _setup_table_model(self, table_model):
        """
        Setup the data model for this table view.
        """
        self.source_model = table_model
        self.source_model.sig_data_edited.connect(self.sig_data_edited.emit)
        self.setModel(self.source_model)

    def _setup_item_delegates(self):
        """
        Setup the item delegates for each column of this table view.
        """
        for i, column in enumerate(self.source_model.columns):
            item_delegate = self.source_model.create_delegate_for_column(
                self, column)
            self.setItemDelegateForColumn(i, item_delegate)

    def _setup_column_visibility_actions(self):
        self._toggle_column_visibility_actions = []
        for i, label in enumerate(self.source_model.horizontal_header_labels):
            action = create_action(
                self, label,
                toggled=(lambda toggle,
                         logical_index=i:
                         self.horizontalHeader().setSectionHidden(
                             logical_index, not toggle)
                         ))
            self._toggle_column_visibility_actions.append(action)
            action.setChecked(not self.horizontalHeader().isSectionHidden(i))

    def _setup_shortcuts(self):
        """
        Setup the various shortcuts available for this tableview.
        """
        # Setup IO actions
        copy_to_clipboard_action = create_action(
            self, _("Copy"),
            icon='copy_clipboard',
            tip=_("Put a copy of the selection on the Clipboard "
                  "so you can paste it somewhere else."),
            triggered=self.copy_to_clipboard,
            shortcut='Ctrl+C')

        self._actions['io'] = [copy_to_clipboard_action]
        self.addActions(self._actions['io'])

        # Setup edit actions.
        edit_item_action = create_action(
            self, _("Edit"),
            icon='edit_database_item',
            tip=_("Edit the currently focused item in this table."),
            triggered=self._edit_current_item,
            shortcut=['Enter', 'Return'],
            context=Qt.WidgetShortcut)
        self.selectionModel().currentChanged.connect(
            lambda current, previous: edit_item_action.setEnabled(
                self.is_data_editable_at(current)))

        clear_item_action = create_action(
            self, _("Clear"),
            icon='erase_data',
            tip=_("Set the currently focused item to NULL."),
            triggered=self._clear_current_item,
            shortcut='Ctrl+Delete',
            context=Qt.WidgetShortcut)
        self.selectionModel().currentChanged.connect(
            lambda current, previous: clear_item_action.setEnabled(
                not self.is_data_required_at(current)))

        save_edits_action = create_action(
            self, _("Save edits"),
            icon='commit_changes',
            tip=_('Save all edits made to the table in the database.'),
            triggered=lambda: self._save_data_edits(force=False),
            shortcut='Ctrl+S',
            context=Qt.WidgetShortcut)
        save_edits_action.setEnabled(False)
        self.sig_data_edited.connect(save_edits_action.setEnabled)

        cancel_edits_action = create_action(
            self, _("Cancel edits"),
            icon='cancel_changes',
            tip=_('Cancel all edits made to the table since last save.'),
            triggered=self._cancel_data_edits,
            shortcut='Ctrl+Delete',
            context=Qt.WidgetShortcut)
        cancel_edits_action.setEnabled(False)
        self.sig_data_edited.connect(cancel_edits_action.setEnabled)

        undo_edits_action = create_action(
            self, _("Undo"),
            icon='undo',
            tip=_('Undo last edit made to the table.'),
            triggered=self._undo_last_data_edit,
            shortcut='Ctrl+Z',
            context=Qt.WidgetShortcut)
        undo_edits_action.setEnabled(False)
        self.sig_data_edited.connect(undo_edits_action.setEnabled)

        self._actions['edit'] = [
            edit_item_action, clear_item_action, undo_edits_action,
            save_edits_action, cancel_edits_action]
        self.addActions(self._actions['edit'])

        # Setup selection actions.
        select_all_action = create_action(
            self, _("Select All"),
            icon='select_all',
            tip=_("Selects all items in the table."),
            triggered=self.selectAll,
            shortcut='Ctrl+A',
            context=Qt.WidgetShortcut)

        select_clear_action = create_action(
            self, _("Clear All"),
            icon='select_clear',
            tip=_("Clears the selection in the table."),
            triggered=lambda _: self.selectionModel().clearSelection(),
            shortcut='Escape',
            context=Qt.WidgetShortcut)

        select_row_action = create_action(
            self, _("Select Row"),
            icon='select_row',
            tip=_("Select the entire row of the current selection. "
                  "If the current selection spans multiple rows, "
                  "all rows that intersect the selection will be selected."),
            triggered=self.select_row,
            shortcut='Shift+Space',
            context=Qt.WidgetShortcut)

        select_column_action = create_action(
            self, _("Select Column"),
            icon='select_column',
            tip=_("Select the entire column of the current selection. "
                  "If the current selection spans multiple columns, all "
                  "columns that intersect the selection will be selected."),
            triggered=self.select_column,
            shortcut='Ctrl+Space',
            context=Qt.WidgetShortcut)

        self._actions['selection'] = [
            select_all_action, select_clear_action, select_row_action,
            select_column_action]
        self.addActions(self._actions['selection'])

        # Setup sort actions.
        sort_ascending_action = create_action(
            self, _("Sort Ascending"),
            icon='sort_ascending',
            tip=_("Reorder rows by sorting the data of the current column "
                  "in ascending order."),
            triggered=lambda _:
                self.sort_by_current_column(Qt.AscendingOrder),
            shortcut="Ctrl+<",
            context=Qt.WidgetShortcut)

        sort_descending_action = create_action(
            self, _("Sort Descending"),
            icon='sort_descending',
            tip=_("Reorder rows by sorting the data of the current column "
                  "in descending order."),
            triggered=lambda _:
                self.sort_by_current_column(Qt.DescendingOrder),
            shortcut="Ctrl+>",
            context=Qt.WidgetShortcut)

        sort_clear_action = create_action(
            self, _("Clear Sort"),
            icon='sort_clear',
            tip=_("Clear all sorts applied to the columns of the table."),
            triggered=lambda _: self.clear_sort(),
            shortcut="Ctrl+.",
            context=Qt.WidgetShortcut)

        self._actions['sort'] = [sort_ascending_action, sort_descending_action,
                                 sort_clear_action]
        self.addActions(self._actions['sort'])

        # Setup move actions.
        for key in ['Up', 'Down', 'Left', 'Right']:
            self.addAction(create_action(
                parent=self,
                triggered=lambda _, key=key: self.move_current_to_border(key),
                shortcut='Ctrl+{}'.format(key),
                context=Qt.WidgetShortcut
                ))
            self.addAction(create_action(
                parent=self,
                triggered=lambda _, key=key:
                    self.extend_selection_to_border(key),
                shortcut='Ctrl+Shift+{}'.format(key),
                context=Qt.WidgetShortcut
                ))

    # ---- Data sorting
    def get_columns_sorting_state(self):
        """
        Return a 2-items tuple where the first item is the logical index
        of the currently sorted column (this value is -1 if there is None)
        and the second item is the sorting order (0 for ascending and
        1 for descending).
        """
        return (self.horizontalHeader().sortIndicatorSection(),
                self.horizontalHeader().sortIndicatorOrder())

    def clear_sort(self):
        """
        Clear all sorts applied to the columns of this table.
        """
        self.horizontalHeader().clear_sort()

    def sort_by_column(self, column_logical_index, sorting_order):
        """
        Sort the rows of this table by ordering the data of the specified
        column in the specified sorting order.
        """
        self.horizontalHeader().sort_by_column(
            column_logical_index, sorting_order)

    def sort_by_current_column(self, sorting_order):
        """
        Sort the rows of this table by ordering the data of the currently
        selected column, if any, in the specified sorting order.
        """
        self.sort_by_column(
            self.selectionModel().currentIndex().column(), sorting_order)

    # ---- Data selection
    def get_selected_rows_data(self):
        """
        Return the data relative to the currently selected rows in this table.
        """
        model_indexes = self.selectionModel().selectedIndexes()
        rows = sorted(list(set(
            [index.row() for index in model_indexes])))
        return self.source_model.dataf.iloc[rows]

    def get_current_row_data(self):
        """
        Return the data relative to the row with the current item (the item
        with the focus).
        """
        model_index = self.selectionModel().currentIndex()
        return (None if not model_index.isValid() else
                self.source_model.dataf.iloc[[model_index.row()]])

    def select_row(self):
        """
        Select the entire row of the current selection. If the current
        selection spans multiple rows, all rows that intersect the selection
        will be selected.
        """
        self.setFocus()
        selected_indexes = self.selectionModel().selectedIndexes()
        selected_rows = sorted(list(set(
            [index.row() for index in selected_indexes])))
        for interval in intervals_extract(selected_rows):
            self.selectionModel().select(
                QItemSelection(self.model().index(interval[0], 0),
                               self.model().index(interval[1], 0)),
                QItemSelectionModel.Select | QItemSelectionModel.Rows)

    def select_column(self):
        """
        Select the entire column of the current selection. If the current
        selection spans multiple columns, all columns that intersect the
        selection will be selected.
        """
        self.setFocus()
        selected_indexes = self.selectionModel().selectedIndexes()
        selected_columns = sorted(list(set(
            [index.column() for index in selected_indexes])))
        for interval in intervals_extract(selected_columns):
            self.selectionModel().select(
                QItemSelection(self.model().index(0, interval[0]),
                               self.model().index(0, interval[1])),
                QItemSelectionModel.Select | QItemSelectionModel.Columns)

    def get_selected_columns(self):
        """
        Return the list of logical indexes corresponding to the columns
        that are currently selected in the table.
        """
        return [index.column() for index in
                self.selectionModel().selectedColumns()]

    def move_current_to_border(self, key):
        """
        Move the currently selected index to the top, bottom, far right or
        far left of this table.
        """
        current_index = self.selectionModel().currentIndex()
        if key == 'Up':
            row = 0
            column = current_index.column()
        elif key == 'Down':
            row = self.model().rowCount() - 1
            column = current_index.column()
        elif key == 'Left':
            row = current_index.row()
            column = self.horizontalHeader().logicalIndex(0)
        elif key == 'Right':
            row = current_index.row()
            column = self.horizontalHeader().logicalIndex(
                self.visible_column_count() - 1)
        self.selectionModel().setCurrentIndex(
            self.model().index(row, column),
            QItemSelectionModel.ClearAndSelect)

    def extend_selection_to_border(self, key):
        """
        Extend the selection adjacent to the current cell to the top, bottom,
        right or left border of this table.
        """
        current_index = self.selectionModel().currentIndex()
        current_visual_column = (
            self.horizontalHeader().visualIndex(current_index.column()))
        self.selectionModel().select(
            current_index, QItemSelectionModel.Select)

        if key in ['Left', 'Right']:
            # We get a list of rows that have selection on the column of
            # the current index.
            rows_with_selection = [
                index.row()
                for index in self.selectionModel().selectedIndexes()
                if index.column() == current_index.column()]

            # Now we determine the top and bottom rows of the row interval
            # over which we need to extend the selection to the left or to
            # the right. of this table.
            for interval in intervals_extract(rows_with_selection):
                if interval[0] <= current_index.row() <= interval[1]:
                    top_row = interval[0]
                    bottom_row = interval[1]
                    break

            # We define the list of logical column indexes for which we need
            # to extend the selection.
            if key == 'Left':
                columns_to_select = sorted(
                    [self.horizontalHeader().logicalIndex(index) for
                     index in range(0, current_visual_column + 1)])
            else:
                columns_to_select = sorted(
                    [self.horizontalHeader().logicalIndex(index) for index in
                     range(current_visual_column, self.visible_column_count())]
                    )
        elif key in ['Up', 'Down']:
            # We get a list of columns that have selection on the row of
            # the current index.
            visual_columns_with_selection = [
                self.horizontalHeader().visualIndex(index.column())
                for index in self.selectionModel().selectedIndexes()
                if index.row() == current_index.row()]

            # Now we determine the left and right columns of the column
            # interval over which we need to extend the selection to the
            # top or the bottom of this table.
            for interval in intervals_extract(visual_columns_with_selection):
                if interval[0] <= current_visual_column <= interval[1]:
                    left_column = interval[0]
                    right_column = interval[1]
                    break

            # We define the list of logical column indexes for which we need
            # to extend the selection.
            columns_to_select = sorted(
                [self.horizontalHeader().logicalIndex(index) for
                 index in range(left_column, right_column + 1)])

            # We determine the top and bottom rows over which we need to
            # extend the columns.
            if key == 'Up':
                top_row = 0
                bottom_row = current_index.row()
            elif key == 'Down':
                top_row = current_index.row()
                bottom_row = self.model().rowCount() - 1

        # We extend the selection between the top and bottom row and
        # left and right column visual indexes.
        selection = QItemSelection()
        for column_interval in intervals_extract(columns_to_select):
            selection.select(
                self.model().index(top_row, column_interval[0]),
                self.model().index(bottom_row, column_interval[1]))
        self.selectionModel().select(
            selection, QItemSelectionModel.Select)

    # ---- Utilities
    def copy_to_clipboard(self):
        """
        Put a copy of the selection on the Clipboard.

        When the selection is composed of nonadjacent cells, the selected
        cells are collapsed together and their content is pasted as a single
        rectangle that *must* be contiguous, or else an error message is
        shown to the user.

        Also see:
        # https://docs.microsoft.com/en-us/office/troubleshoot/excel/command-cannot-be-used-on-selections
        """
        selected_indexes = sorted(
            self.selectionModel().selectedIndexes(), key=lambda v: v.row())
        selected_columns = [
            sorted([index.column() for index in group]) for key, group in
            itertools.groupby(selected_indexes, lambda v: v.row())]

        if not selected_columns[1:] == selected_columns[:-1]:
            QMessageBox.information(
                self, __appname__,
                _("This function cannot be used with multiple selections."),
                buttons=QMessageBox.Ok
                )
        else:
            collapsed_selection = [
                sorted(group, key=lambda v: v.column()) for key, group in
                itertools.groupby(selected_indexes, lambda v: v.row())]
            selected_text = '\n'.join(
                '\t'.join(index.data() for index in row)
                for row in collapsed_selection)
            QApplication.clipboard().setText(selected_text)

    def row_count(self):
        """Return this table number of visible row."""
        return self.model().rowCount()

    def selected_row_count(self):
        """
        Return the number of rows of this table that have at least one
        selected items.
        """
        return len(self.get_selected_rows_data())

    def visible_row_count(self):
        """Return this table number of visible rows."""
        return self.model().rowCount()

    # ---- Column options
    def column_count(self):
        """Return this table number of visible and hidden columns."""
        return self.horizontalHeader().count()

    def hidden_column_count(self):
        """Return this table number of hidden columns."""
        return self.horizontalHeader().hiddenSectionCount()

    def visible_column_count(self):
        """Return this table number of visible columns."""
        return self.column_count() - self.hidden_column_count()

    def get_horiz_header_state(self):
        """
        Return the current state of this table horizontal header.
        """
        return qbytearray_to_hexstate(self.horizontalHeader().saveState())

    def restore_horiz_header_state(self, hexstate):
        """
        Restore the state of this table horizontal header from hexstate.
        """
        if hexstate is not None:
            self.horizontalHeader().restoreState(
                hexstate_to_qbytearray(hexstate))
        for i, action in enumerate(self.get_column_visibility_actions()):
            action.blockSignals(True)
            action.setChecked(not self.horizontalHeader().isSectionHidden(i))
            action.blockSignals(False)

    def show_all_available_columns(self):
        """
        Set the visibility of all available columns of this table to true.
        """
        for action in self._toggle_column_visibility_actions:
            action.setChecked(True)

    def restore_horiz_header_to_defaults(self):
        """
        Restore the visibility and order of this table columns to the
        default values.
        """
        self.show_all_available_columns()
        for logical_index, column in enumerate(self.source_model.columns):
            self.horizontalHeader().moveSection(
                self.horizontalHeader().visualIndex(logical_index),
                logical_index)
        self.resizeColumnsToContents()

    def get_column_visibility_actions(self):
        """
        Return a list of QAction for toggling on/off the visibility of this
        table column.
        """
        return self._toggle_column_visibility_actions

    # ---- Data edits
    def is_data_editable_at(self, model_index):
        """
        Return whether the item at the specified model index is editable.
        """
        return not isinstance(
            self.itemDelegate(model_index), NotEditableDelegate)

    def is_data_required_at(self, model_index):
        """
        Return whether a non null value is required for the item at the
        specified model index.
        """
        return self.itemDelegate(model_index).is_required

    def contextMenuEvent(self, event):
        """
        Override Qt method to show a context menu that shows different actions
        available for the cell.
        """
        menu = QMenu(self)
        sections = list(self._actions.keys())
        for section in sections:
            for action in self._actions[section]:
                menu.addAction(action)
            if section != sections[-1]:
                menu.addSeparator()
        menu.popup(QCursor.pos())

    def _clear_current_item(self):
        """
        Set current item's data to None.
        """
        current_index = self.selectionModel().currentIndex()
        if current_index.isValid():
            self.itemDelegate(current_index).clear_model_data(current_index)

    def _edit_current_item(self):
        """
        Turn on edit mode for this table current cell.
        """
        current_index = self.selectionModel().currentIndex()
        if current_index.isValid():
            if self.state() != self.EditingState:
                self.selectionModel().setCurrentIndex(
                    current_index, self.selectionModel().Select)
                self.edit(current_index)
            else:
                self.itemDelegate(current_index).commit_data()

    def _cancel_data_edits(self):
        """
        Cancel all the edits that were made to the table data of this view
        since last save.
        """
        self.model().cancel_all_data_edits()

    def _undo_last_data_edit(self):
        """
        Undo the last data edits that was added to the table.
        An update of the view is forced if  update_model_view is True.
        """
        self.model().undo_last_data_edit()

    def _save_data_edits(self, force=True):
        """
        Save the data edits to the database. If 'force' is 'False', a message
        is first shown before proceeding.
        """
        if force is False:
            reply = QMessageBox.warning(
                self, _('Save changes'),
                _("This will permanently save the changes made in this "
                  "table in the database.<br><br>"
                  "This action <b>cannot</b> be undone."),
                buttons=QMessageBox.Ok | QMessageBox.Cancel
                )
            if reply == QMessageBox.Cancel:
                return
        self.model().save_data_edits()

    def raise_edits_error(self, model_index, message):
        """"
        Raise a modal dialog that shows the specifed error message that
        occured while editing the data at the specifed model index.
        When the dialog is closed by the user, the focus is given back
        the last edited cell and edit mode is turned on again, so that the
        the user can correct the invalid edits accordingly.
        """
        QMessageBox.critical(
            self, _('Edits error'),
            message,
            buttons=QMessageBox.Ok)
        self.setCurrentIndex(model_index)
        self._edit_current_item()
        self.model().undo_last_data_edit()

    def edit(self, model_index, trigger=None, event=None):
        """
        Extend Qt method to ensure that the cell of this table that is
        going to be edited is visible.
        """
        if trigger is None:
            # Scroll to item if it is not currently visible in the scrollarea.
            item_rect = self.visualRect(model_index)
            view_rect = self.geometry()
            if not view_rect.contains(item_rect):
                self.scrollTo(model_index, hint=self.EnsureVisible)

            return super().edit(model_index)
        else:
            return super().edit(model_index, trigger, event)


class SardesTableWidget(SardesPaneWidget):

    def __init__(self, table_model, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)

        self.tableview = SardesTableView(table_model)
        self.set_central_widget(self.tableview)

        self._setup_upper_toolbar()
        self._setup_status_bar()

    # ---- Public methods
    def get_table_title(self):
        """Return the title of this widget's table."""
        return self.tableview.source_model.TABLE_TITLE

    def get_table_id(self):
        """Return the ID of this widget's table."""
        return self.tableview.source_model.TABLE_ID

    # ---- Setup
    def _setup_upper_toolbar(self):
        """
        Setup the upper toolbar of this table widget.
        """
        super()._setup_upper_toolbar()
        toolbar = self.get_upper_toolbar()

        sections = list(self.tableview._actions.keys())
        for section in sections:
            for action in self.tableview._actions[section]:
                toolbar.addAction(action)
            if section != sections[-1]:
                toolbar.addSeparator()

        # We add a stretcher here so that the columns options button is
        # aligned to the right side of the toolbar.
        self._upper_toolbar_separator = toolbar.addWidget(
            create_toolbar_stretcher())

        toolbar.addWidget(self._create_columns_options_button())

    def _setup_status_bar(self):
        """
        Setup the status bar of this table widget.
        """
        statusbar = self.statusBar()
        statusbar.setSizeGripEnabled(False)

        # Number of row(s) selected.
        self.selected_line_count = QLabel()
        statusbar.addPermanentWidget(self.selected_line_count)

        self._update_line_count()
        self.tableview.selectionModel().selectionChanged.connect(
            self._update_line_count)
        self.tableview.model().rowsRemoved.connect(
            self._update_line_count)
        self.tableview.model().rowsInserted.connect(
            self._update_line_count)
        self.tableview.model().modelReset.connect(
            self._update_line_count)

    @property
    def db_connection_manager(self):
        """
        Return the database connection manager associated with the model
        of this table widget.
        """
        return self.tableview.source_model.db_connection_manager

    # ---- Line count
    def _update_line_count(self):
        """
        Update the text of the selected/total row count indicator.
        """
        text = _("{} out of {} row(s) selected").format(
            self.tableview.selected_row_count(),
            self.tableview.visible_row_count())
        self.selected_line_count.setText(text + ' ')

    # ---- Toolbar
    def add_toolbar_widget(self, widget, which='upper'):
        """
        Add a new widget to the uppermost toolbar if 'which' is 'upper',
        else add it to the lowermost toolbar.
        """
        if which == 'upper':
            self.get_upper_toolbar().insertWidget(
                self._upper_toolbar_separator, widget)
        else:
            self.get_lower_toolbar().addWidget(widget)

    def add_toolbar_separator(self, which='upper'):
        """
        Add a new separator to the uppermost toolbar if 'which' is 'upper',
        else add it to the lowermost toolbar.
        """
        if which == 'upper':
            self.get_upper_toolbar().insertSeparator(
                self._upper_toolbar_separator)
        else:
            self.get_lower_toolbar().addSeparator()

    # ---- Table view header state
    def get_table_horiz_header_state(self):
        """
        Return the current state of this table horizontal header.
        """
        return self.tableview.get_horiz_header_state()

    def restore_table_horiz_header_state(self, hexstate):
        """
        Restore the state of this table horizontal header from hexstate.
        """
        self.tableview.restore_horiz_header_state(hexstate)

    # ---- Columns option toolbutton
    def _create_columns_options_button(self):
        """
        Create and return a toolbutton with a menu that contains actions
        to toggle the visibility of the available columns of this table.
        """
        # Create the column options button.
        toolbutton = create_toolbutton(
            self,
            icon='table_columns',
            text=_("Column options"),
            tip=_("Open a menu to select the columns to "
                  "display in this table."),
            iconsize=get_iconsize()
            )
        toolbutton.setPopupMode(toolbutton.InstantPopup)

        # Create the column options menu.
        menu = QMenu()
        toolbutton.setMenu(menu)

        # Add a show all column and restore to defaults action.
        menu.addAction(create_action(
            self, _('Restore to defaults'),
            triggered=self.tableview.restore_horiz_header_to_defaults))
        menu.addAction(create_action(
            self, _('Show all'),
            triggered=self.tableview.show_all_available_columns))

        # Add an action to toggle the visibility for each available
        # column of this table.
        menu.addSeparator()
        for action in self.tableview.get_column_visibility_actions():
            menu.addAction(action)

        # We store a reference to this button to access it more
        # easily during testing.
        self._column_options_button = toolbutton
        return toolbutton


if __name__ == '__main__':
    from sardes.database.database_manager import DatabaseConnectionManager
    app = QApplication(sys.argv)

    manager = DatabaseConnectionManager()
    table_view = SardesTableView(manager)
    table_view.show()
    manager.connect_to_db('debug')

    sys.exit(app.exec_())
