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
import itertools

# ---- Third party imports
import pandas as pd
from qtpy.QtCore import (QAbstractTableModel, QEvent, QModelIndex,
                         QSortFilterProxyModel, Qt, QVariant, Signal, Slot,
                         QItemSelection, QItemSelectionModel, QRect)
from qtpy.QtGui import QColor, QCursor
from qtpy.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox,
                            QHeaderView, QLabel, QLineEdit, QMenu, QMessageBox,
                            QSpinBox, QStyledItemDelegate, QTableView,
                            QTextEdit)

# ---- Local imports
from sardes import __appname__
from sardes.api.panes import SardesPaneWidget
from sardes.config.locale import _
from sardes.config.gui import get_iconsize
from sardes.utils.data_operations import intervals_extract
from sardes.utils.qthelpers import (
    create_action, create_toolbutton, create_toolbar_stretcher,
    qbytearray_to_hexstate, hexstate_to_qbytearray)


# =============================================================================
# ---- Delegates
# =============================================================================
class NotEditableDelegate(QStyledItemDelegate):
    """
    A delegate used to indicate that the items in the associated
    column are not editable.
    """

    def createEditor(self, *args, **kargs):
        """Qt method override."""
        return None


class SardesItemDelegateBase(QStyledItemDelegate):
    """
    Basic functionality for Sardes item delegates.

    WARNING: Don't override any methods or attributes present here.
    """

    def __init__(self, model_view, unique_constraint=False):
        super() .__init__(parent=model_view)
        self.model_view = model_view
        self.model_index = None
        self.editor = None
        self._unique_constraint = unique_constraint

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

            # We store the edits even though they are not validated, so that
            # when we return to this delegate to edits, the last value
            # entered by the user is preserved.
            self.model.set_data_edits_at(self.model_index, editor_value)
            if error_message is not None:
                self.model_view.raise_edits_error(
                    self.model_index, error_message)

    # ---- Public methods
    @property
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
        field_name = self.model.get_horizontal_header_label_at(
            self.model_index.column())
        edited_value = self.get_editor_data()
        if (self._unique_constraint and self.model.is_value_in_column(
                self.model_index, edited_value)):
            return _(
                "<b>Duplicate key value violates unique constraint.</b>"
                "<br><br>"
                "The {} <i>{}</i> already exists. Please use another value"
                ).format(field_name, edited_value, field_name)
        else:
            return None


class SardesItemDelegate(SardesItemDelegateBase):
    """
    Sardes item delegates to edit the data of displayed in a table view.

    Specific delegates *can* inherit this class and reimplement its interface.
    """

    def __init__(self, *args, **kargs):
        super() .__init__(*args, **kargs)

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
        else:
            raise NotImplementedError

    def validate_edits(self):
        """Validate the value of this item delegate's editor."""
        return None


class TextEditDelegate(SardesItemDelegate):
    """
    A delegate to edit very long strings that can span over multiple lines.
    """

    def __init__(self, model_view):
        super() .__init__(model_view, unique_constraint=False)

    def create_editor(self, parent):
        return QTextEdit(parent)


class StringEditDelegate(SardesItemDelegate):
    """
    A delegate to edit a 250 characters strings.
    """
    MAX_LENGTH = 250

    def __init__(self, model_view, unique_constraint=False):
        super() .__init__(model_view, unique_constraint=unique_constraint)

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

    def __init__(self, parent=None):
        super() .__init__(parent)

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

    def __init__(self, model_index):
        super() .__init__()
        self.model_index = model_index


class ValueChanged(object):
    """
    A class that represent a change of a value at a given model index.
    """

    def __init__(self, model_index, edited_value,
                 dataf_index, dataf_column, dataf_value):
        super() .__init__()
        self.model_index = model_index
        self.edited_value = edited_value

        self.dataf_index = dataf_index
        self.dataf_column = dataf_column
        self.dataf_value = dataf_value

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

    # A list of tuple that maps the keys of the columns dataframe with their
    # corresponding human readable label to use in the GUI.
    __data_columns_mapper__ = []

    def __init__(self, db_connection_manager=None):
        super().__init__()
        self._data_columns_mapper = OrderedDict(self.__data_columns_mapper__)

        # A pandas dataframe containing the data that are shown in the
        # database.
        self.dataf = pd.DataFrame([])

        # A list containing the edits made by the user to the
        # content of this table's model data in chronological order.
        self._dataf_edits = []
        self._edited_data = {}
        self._new_rows = []
        self._deleted_rows = []

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
        self._dataf_edits = []
        self._edited_data = {}
        self._new_rows = []
        self._deleted_rows = []

        self.modelReset.emit()
        self.sig_data_edited.emit(False)

    def rowCount(self, parent=QModelIndex()):
        """Qt method override. Return the number of row of the table."""
        return len(self.dataf)

    def data(self, index, role=Qt.DisplayRole):
        """Qt method override."""
        column_key = self.columns[index.column()]
        row = index.row()
        try:
            column = self.dataf.columns.get_loc(column_key)
        except KeyError:
            column = None

        if role == Qt.DisplayRole:
            if column is None:
                value = ''
            else:
                value = self.get_edited_data_at(index)
                if isinstance(value, NoDataEdit):
                    value = self.dataf.iloc[row, column]
                value = '' if (pd.isna(value) or value is None) else value
            if pd.api.types.is_bool(value):
                value = _('Yes') if value else _('No')
            return str(value)
        elif role == Qt.ForegroundRole:
            return QVariant()
        elif role == Qt.BackgroundRole:
            return (QVariant() if
                    isinstance(self.get_edited_data_at(index), NoDataEdit)
                    else QColor('#CCFF99'))
        elif role == Qt.ToolTipRole:
            return (QVariant() if column is None
                    else self.dataf.iloc[row, column])
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
        column_key = self.columns[model_index.column()]
        try:
            dataf_column = self.dataf.columns.get_loc(column_key)
        except KeyError:
            value = None
        else:
            dataf_row = model_index.row()
            value = self.dataf.iloc[dataf_row, dataf_column]
        return value

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
        # First we check if value is found in the edited data.
        for edited_index, edited_value in self._edited_data.items():
            if (edited_index.column() == model_index.column() and
                    (edited_value == value)):
                return True
        else:
            # Else we check if the value is found in the unedited data
            # of this model's data.
            dataf_column = self.columns[model_index.column()]
            isin_indexes = self.dataf[self.dataf[dataf_column].isin([value])]
            return any([
                not self.is_data_edited_at(self.index(
                    self.dataf.index.get_loc(index), model_index.column()))
                for index in isin_indexes.index
                ])

    # ---- Data edits
    def has_unsaved_data_edits(self):
        """
        Return whether any edits were made to the table's data since last save.
        """
        return bool(len(self._edited_data))

    def is_data_edited_at(self, model_index):
        """
        Return whether edits were made at the specified model index
        since last save.
        """
        return model_index in self._edited_data

    def cancel_all_data_edits(self):
        """
        Cancel all the edits that were made to the table data since last save.
        """
        self._dataf_edits = []
        self._edited_data = {}
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1))
        self.sig_data_edited.emit(False)

    def get_edited_data_at(self, model_index):
        """
        Return the edited value, if any, that was made at the specified
        model index since last save.
        """
        return self._edited_data.get(model_index, NoDataEdit(model_index))

    def set_data_edits_at(self, model_index, edited_value):
        """
        Store the value that was edited at the specified model index.
        A signal is also emitted to indicate that the data were edited,
        so that the GUI can be updated accordingly.
        """
        dataf_value = self.get_dataf_value_at(model_index)
        dataf_index = self.dataf.index[model_index.row()]
        dataf_column = self.columns[model_index.column()]

        # We store the edited value until it is commited and
        # saved to the database.
        self._dataf_edits.append(
            ValueChanged(model_index, edited_value,
                         dataf_index, dataf_column, dataf_value))

        # We add the model index to the list of indexes whose value have
        # been edited if the edited value differ from the value saved in
        # the model's data.
        if dataf_value != edited_value:
            self._edited_data[model_index] = edited_value
        else:
            if model_index in self._edited_data:
                del self._edited_data[model_index]

        self.sig_data_edited.emit(self.has_unsaved_data_edits())
        self.dataChanged.emit(model_index, model_index)

    def undo_last_data_edit(self, update_model_view=True):
        """
        Undo the last data edits that was added to the stack.
        An update of the view is forced if  update_model_view is True.
        """
        if len(self._dataf_edits) == 0:
            return

        # Undo the last edit.
        last_edit = self._dataf_edits.pop(-1)
        if last_edit.model_index in self._edited_data:
            del self._edited_data[last_edit.model_index]

        # Check if there was a previous edit for this model index in the stack.
        for edit in reversed(self._dataf_edits):
            if edit.model_index == last_edit.model_index:
                self._edited_data[edit.model_index] = edit.edited_value
                break

        if update_model_view:
            self.dataChanged.emit(last_edit.model_index, last_edit.model_index)
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

    # ---- Data edits
    def save_data_edits(self):
        """
        Save all data edits to the database.
        """
        raise NotImplementedError


class SardesSortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, source_model):
        super().__init__()
        self.setSourceModel(source_model)
        self.setSortCaseSensitivity(False)

    # ---- Qt methods override
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        Override Qt method so that the visual indexes of the rows are shown in
        the vertical header of the table instead of their logical indexes.
        """
        return self.sourceModel().headerData(section, orientation, role)

    # ---- Source model methods
    def cancel_all_data_edits(self):
        self.sourceModel().cancel_all_data_edits()

    def fetch_model_data(self, *args, **kargs):
        self.sourceModel().fetch_model_data()

    def get_value_at(self, proxy_index):
        return self.sourceModel().get_value_at(self.mapToSource(proxy_index))

    def get_horizontal_header_label_at(self, column_or_index):
        return self.sourceModel().get_horizontal_header_label_at(
            column_or_index)

    def has_unsaved_data_edits(self):
        return self.sourceModel().has_unsaved_data_edits()

    def is_value_in_column(self, proxy_index, value):
        return self.sourceModel().is_value_in_column(
            self.mapToSource(proxy_index), value)

    def save_data_edits(self):
        self.sourceModel().save_data_edits()

    def set_data_edits_at(self, proxy_index, value):
        self.sourceModel().set_data_edits_at(
            self.mapToSource(proxy_index), value)

    def undo_last_data_edit(self, update_model_view=True):
        self.sourceModel().undo_last_data_edit(update_model_view)


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
        self.setAlternatingRowColors(True)
        self.setCornerButtonEnabled(True)
        self.setHorizontalHeader(SardesHeaderView(parent=self))
        self.setEditTriggers(self.NoEditTriggers)
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
        self.proxy_model = SardesSortFilterProxyModel(self.source_model)
        self.setModel(self.proxy_model)

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
            shortcut=['Ctrl+Enter', 'Ctrl+Return'])
        self.selectionModel().currentChanged.connect(
            lambda current, previous: edit_item_action.setEnabled(
                self.is_data_editable_at(current)))

        save_edits_action = create_action(
            self, _("Save edits"),
            icon='commit_changes',
            tip=_('Save all edits made to the table in the database.'),
            triggered=lambda: self._save_data_edits(force=False),
            shortcut='Ctrl+S')
        save_edits_action.setEnabled(False)
        self.sig_data_edited.connect(save_edits_action.setEnabled)

        cancel_edits_action = create_action(
            self, _("Cancel edits"),
            icon='cancel_changes',
            tip=_('Cancel all edits made to the table since last save.'),
            triggered=self._cancel_data_edits,
            shortcut='Ctrl+Delete')
        cancel_edits_action.setEnabled(False)
        self.sig_data_edited.connect(cancel_edits_action.setEnabled)

        undo_edits_action = create_action(
            self, _("Undo"),
            icon='undo',
            tip=_('Undo last edit made to the table.'),
            triggered=self._undo_last_data_edit,
            shortcut='Ctrl+Z')
        undo_edits_action.setEnabled(False)
        self.sig_data_edited.connect(undo_edits_action.setEnabled)

        self._actions['edit'] = [
            edit_item_action, save_edits_action, cancel_edits_action,
            undo_edits_action]
        self.addActions(self._actions['edit'])

        # Setup selection actions.
        select_all_action = create_action(
            self, _("Select All"),
            icon='select_all',
            tip=_("Selects all items in the table."),
            triggered=self.selectAll,
            shortcut='Ctrl+A')

        select_clear_action = create_action(
            self, _("Clear All"),
            icon='select_clear',
            tip=_("Clears the selection in the table."),
            triggered=lambda _: self.selectionModel().clearSelection(),
            shortcut='Escape')

        select_row_action = create_action(
            self, _("Select Row"),
            icon='select_row',
            tip=_("Select the entire row of the current selection. "
                  "If the current selection spans multiple rows, "
                  "all rows that intersect the selection will be selected."),
            triggered=self.select_row,
            shortcut='Shift+Space',
            context=Qt.WindowShortcut)

        select_column_action = create_action(
            self, _("Select Column"),
            icon='select_column',
            tip=_("Select the entire column of the current selection. "
                  "If the current selection spans multiple columns, all "
                  "columns that intersect the selection will be selected."),
            triggered=self.select_column,
            shortcut='Ctrl+Space')

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
            shortcut="Ctrl+<")

        sort_descending_action = create_action(
            self, _("Sort Descending"),
            icon='sort_descending',
            tip=_("Reorder rows by sorting the data of the current column "
                  "in descending order."),
            triggered=lambda _:
                self.sort_by_current_column(Qt.DescendingOrder),
            shortcut="Ctrl+>")

        sort_clear_action = create_action(
            self, _("Clear Sort"),
            icon='sort_clear',
            tip=_("Clear all sorts applied to the columns of the table."),
            triggered=lambda _: self.clear_sort(),
            shortcut="Ctrl+.")

        self._actions['sort'] = [sort_ascending_action, sort_descending_action,
                                 sort_clear_action]
        self.addActions(self._actions['sort'])

        # Setup move actions.
        for key in ['Up', 'Down', 'Left', 'Right']:
            self.addAction(create_action(
                parent=self,
                triggered=lambda _, key=key: self.move_current_to_border(key),
                shortcut='Ctrl+{}'.format(key)
                ))
            self.addAction(create_action(
                parent=self,
                triggered=lambda _, key=key:
                    self.extend_selection_to_border(key),
                shortcut='Ctrl+Shift+{}'.format(key)
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
        proxy_indexes = self.selectionModel().selectedIndexes()
        rows = sorted(list(set(
            [self.proxy_model.mapToSource(i).row() for i in proxy_indexes]
            )))
        return self.source_model.dataf.iloc[rows]

    def get_selected_row_data(self):
        """
        Return the data relative to the currently selected row in this table.
        If more than one row is selected, the data from the first row of the
        selection is returned.
        """
        selected_data = self.get_selected_rows_data()
        if len(selected_data) > 0:
            row_data = selected_data.iloc[[0]]
        else:
            row_data = None
        return row_data

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
        return self.proxy_model.rowCount()

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

    def _edit_current_item(self):
        """
        Turn on edit mode for this table current cell.
        """
        current_index = self.selectionModel().currentIndex()
        if current_index.isValid():
            if self.state() != self.EditingState:
                self.selectionModel().clearSelection()
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
        self.model().undo_last_data_edit(update_model_view=False)

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

        self.tableview = SardesTableView(table_model)
        self.set_central_widget(self.tableview)

        self._setup_upper_toolbar()
        self._setup_status_bar()

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
