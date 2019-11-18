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
from datetime import datetime
import itertools
from math import floor, ceil

# ---- Third party imports
import pandas as pd
from qtpy.QtCore import (QEvent, Qt, Signal, Slot, QItemSelection,
                         QItemSelectionModel, QRect)
from qtpy.QtGui import QCursor, QPen
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
        return self.model_view.model()

    def get_model_data(self):
        """
        Return the value stored in the model at the model index
        corresponding to this item delegate.
        """
        return self.model().get_value_at(self.model_index)

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
    sig_data_edited = Signal(bool, bool)
    sig_show_event = Signal()

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

    def showEvent(self, *args, **kargs):
        self.sig_show_event.emit()
        super().showEvent(*args, **kargs)

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
        self.sig_data_edited.connect(
            lambda v1, v2: save_edits_action.setEnabled(v1))

        cancel_edits_action = create_action(
            self, _("Cancel edits"),
            icon='cancel_changes',
            tip=_('Cancel all edits made to the table since last save.'),
            triggered=self._cancel_data_edits,
            shortcut='Ctrl+Delete',
            context=Qt.WidgetShortcut)
        cancel_edits_action.setEnabled(False)
        self.sig_data_edited.connect(
            lambda v1, v2: cancel_edits_action.setEnabled(v1))

        undo_edits_action = create_action(
            self, _("Undo"),
            icon='undo',
            tip=_('Undo last edit made to the table.'),
            triggered=self._undo_last_data_edit,
            shortcut='Ctrl+Z',
            context=Qt.WidgetShortcut)
        undo_edits_action.setEnabled(False)
        self.sig_data_edited.connect(
            lambda v1, v2: undo_edits_action.setEnabled(v2))

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
        dataf_indexes = list(set(
            [self.model().dataf_index_at(index) for index in
             self.selectionModel().selectedIndexes()]
            ))

        selected_dataf = self.source_model.dataf.loc[dataf_indexes]
        if self.model()._sort_by_columns is not None:
            selected_dataf.sort_values(
                by=self.model()._sort_by_columns,
                ascending=(self.model()._sort_order == Qt.AscendingOrder),
                inplace=True)
        return selected_dataf

    def get_current_row_data(self):
        """
        Return the data relative to the row with the current item (the item
        with the focus).
        """
        model_index = self.selectionModel().currentIndex()
        if model_index.isValid():
            return self.source_model.dataf.loc[[
                self.model().dataf_index_at(model_index)]]
        else:
            return None

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
        self.selectionModel().clearSelection()
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

    def model(self):
        """
        Return the model associated with this table widget.
        """
        return self.tableview.model()

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
