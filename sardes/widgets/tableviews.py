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
import numpy as np
import pandas as pd
from qtpy.QtCore import (QEvent, Qt, Signal, Slot, QItemSelection, QSize,
                         QItemSelectionModel, QRect, QTimer, QModelIndex)
from qtpy.QtGui import QCursor, QPen, QPalette
from qtpy.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QDateTimeEdit,
    QDoubleSpinBox, QHeaderView, QLabel, QLineEdit, QMenu, QMessageBox,
    QSpinBox, QStyledItemDelegate, QTableView, QTextEdit, QListView, QStyle,
    QStyleOption, QWidget, QGridLayout, QStyleOptionHeader, QVBoxLayout,
    QTabWidget)

# ---- Local imports
from sardes import __appname__
from sardes.api.panes import SardesPaneWidget
from sardes.api.tablemodels import SardesSortFilterModel, SardesTableModelBase
from sardes.config.icons import get_icon
from sardes.config.locale import _
from sardes.config.gui import get_iconsize
from sardes.utils.data_operations import intervals_extract, are_values_equal
from sardes.utils.qthelpers import (
    create_action, create_toolbutton, create_toolbar_stretcher,
    qbytearray_to_hexstate, hexstate_to_qbytearray, qdatetime_from_datetime,
    get_datetime_from_editor)
from sardes.widgets.statusbar import ProcessStatusBar

# Define the minimum amount of time that the tables wait spinner are shown.
# Otherwise, for very short process, it only flashes in the screen.
MSEC_MIN_PROGRESS_DISPLAY = 500


# =============================================================================
# ---- Delegates
# =============================================================================
class SardesItemDelegateBase(QStyledItemDelegate):
    """
    Basic functionality for Sardes item delegates.

    WARNING: Don't override any methods or attributes present here unless you
    know what you are doing.
    """

    def __init__(self, model_view, unique_constraint=False,
                 is_required=False):
        super() .__init__(parent=model_view)
        self.model_view = model_view
        self._model_index = None
        self.editor = None
        self.unique_constraint = unique_constraint
        self.is_required = is_required
        self.is_editable = True
        self._widget = QListView()

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
        style = self._widget.style()

        # We remove the State_HasFocus from the option so that Qt doesn't
        # paint it. We paint our own focus rectangle instead.
        has_focus = bool(option.state & QStyle.State_HasFocus)
        option.state &= ~ QStyle.State_HasFocus

        # We dont want cells to be highlighted because of mouse over.
        option.state &= ~QStyle.State_MouseOver

        # We must set the text ouselves or else no text is painted.
        option.text = index.data() if not option.text else option.text

        # Set the color of the text from the model's data.
        foreground_color = index.data(Qt.ForegroundRole)
        if foreground_color:
            option.palette.setColor(QPalette.Text, foreground_color)

        # We must fill the background with a solid color before painting the
        # control. This is necessary, for example, to color the background of
        # the cells with un-saved edits.
        painter.fillRect(option.rect, index.data(Qt.BackgroundRole))
        style.drawControl(
            QStyle.CE_ItemViewItem, option, painter, self._widget)

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
            """Commit edits on Enter or Return key press."""
            key_cond = event.key() in (Qt.Key_Return, Qt.Key_Enter)
            # Shift + Enter is used to insert a line break in a cell.
            mod_cond = not event.modifiers() & Qt.ShiftModifier
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
        if not are_values_equal(editor_value, model_value):
            # We need to validate the edits before submitting the edits to
            # the model or else, unique check will always return an error.
            error_message = self.validate_edits()

            # We store the edits even if the validation fails, so that
            # when we return to this delegate to edits, the last value
            # entered by the user is preserved.
            self.model().set_data_edit_at(self.model_index, editor_value)
            if error_message is not None:
                self.model_view.raise_edits_error(
                    self.model_index, error_message)
            self.model_view._ensure_visible(self.model_index)
            self.model_view.setCurrentIndex(self.model_index)

    # ---- Public methods
    def model(self):
        """
        Return the model whose data this item delegate is used to edit.
        """
        return self.model_view.model()

    @property
    def model_index(self):
        """
        Return the model index associated with this item delegate.
        """
        try:
            return self.model().mapFromSource(self._model_index)
        except AttributeError:
            return self._model_index

    @model_index.setter
    def model_index(self, index):
        """
        Set the model index associated with this item delegate.
        """
        # We store a reference of the source model index because the
        # index from the sort filter proxy model changes if the sort filter
        # proxy model gets invalidated.
        try:
            self._model_index = self.model().mapToSource(index)
        except AttributeError:
            self._model_index = index

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

    def clear_model_data_at(self, model_index):
        """
        Set the data of the model index associated with this delegate to
        a null value.

        Note that we need to pass the model index as an argument, else
        it won't be possible to clear the data if the editor have not been
        created at least once.
        """
        if not self.is_required and model_index.isValid():
            source_model_index = self.model().mapToSource(model_index)
            model_index.model().set_data_edit_at(model_index, None)
            model_index = self.model().mapFromSource(source_model_index)
            self.model_view._ensure_visible(model_index)
            self.model_view.setCurrentIndex(model_index)


class NotEditableDelegate(SardesItemDelegateBase):
    """
    A delegate used to indicate that the items in the associated
    column are not editable.
    """

    def __init__(self, model_view):
        super().__init__(model_view, is_required=True)
        self.is_editable = False

    def createEditor(self, *args, **kargs):
        return None

    def setEditorData(self, editor, index):
        pass

    def setModelData(self, editor, model, index):
        pass

    def clear_model_data_at(self, model_index):
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

    def set_editor_data(self, value):
        """
        Set the value of this item delegate's editor.

        You may need to reimplement this method if the type of your
        item delegate's editor is not supported or else a NotImplementedError
        will be raised.
        """
        if isinstance(self.editor, (QTextEdit, QLineEdit)):
            value = '' if (pd.isna(value) or value is None) else value
            self.editor.setText(value)
        elif isinstance(self.editor, (QSpinBox, QDoubleSpinBox)):
            if not pd.isnull(value):
                self.editor.setValue(value)
        elif isinstance(self.editor, QComboBox):
            for i in range(self.editor.count()):
                if self.editor.itemData(i) == value:
                    self.editor.setCurrentIndex(i)
                    break
            else:
                self.editor.setCurrentIndex(0)
        elif isinstance(self.editor, (QDateEdit, QDateTimeEdit)):
            value = (datetime.today() if (pd.isna(value) or value is None)
                     else value)
            self.editor.setDateTime(qdatetime_from_datetime(value))
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

    def __init__(self, model_view, display_format=None, is_required=False):
        super() .__init__(model_view, is_required=is_required)
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
class RowCountLabel(QLabel):
    """
    A Qt label to display the number of selected rows out of the total number
    of rows shown in a SardesTableView.
    """

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        self._registered_tables = []
        self._last_focused_table = None
        self.set_row_count(0, 0)

    def set_row_count(self, selected_row_count, visible_row_count):
        """
        Set the text displayed by this rowcount label.
        """
        self.setText(_("{} out of {} row(s) selected" + " ")
                     .format(selected_row_count, visible_row_count))

    def register_table(self, table):
        """
        Register the given table to this rowcount label.
        """
        if table not in self._registered_tables:
            self._registered_tables.append(table)
            table.sig_rowcount_changed.connect(self._on_rowcount_changed)
            table.installEventFilter(self)
            if table.hasFocus():
                self.set_row_count(
                    table.selected_row_count(), table.visible_row_count())

    def unregister_table(self, table):
        """
        Un-register the given table from this rowcount label.
        """
        if table in self._registered_tables:
            if table == self._last_focused_table:
                self.set_row_count(0, 0)
            self._registered_tables.remove(table)
            table.removeEventFilter(self)
            table.sig_rowcount_changed.disconnect(self._on_rowcount_changed)

    def _on_rowcount_changed(self, table, selected_count, visible_count):
        """
        Update the selected and total row count displayed by this label after
        a change was made to a registered table if it has focus.
        """
        if table == self._last_focused_table:
            self.set_row_count(selected_count, visible_count)

    def eventFilter(self, table, event):
        """
        Handle FocusIn and Close event for the registered tables.
        """
        if event.type() == QEvent.FocusIn:
            if self._last_focused_table != table:
                self._last_focused_table = table
                self.set_row_count(
                    table.selected_row_count(), table.visible_row_count())
        elif event.type() == [QEvent.Close, QEvent.Hide]:
            if self._last_focused_table == table:
                self._last_focused_table = None
                self.set_row_count(0, 0)
        return super().eventFilter(table, event)


class SardesHeaderView(QHeaderView):
    """
    An horizontal header view that allow sorting by columns on double mouse
    click events (instead of single mouse clicks) and allow to clear the
    sorting of it's associated table view.
    """
    sig_sort_by_column = Signal(int, int)

    def __init__(self, parent, sections_movable=True,
                 orientation=Qt.Horizontal):
        """
        Parameters
        ----------
        parent : QtWidgets.Widgets
            A Qt widget to be set as the parent of this header view.
        sections_movable : bool, optional
            If sections_movable is True, the header sections may be moved
            by the user, otherwise they are fixed in place.
            The default is True.
        orientation : Qt.Orientation, optional
            Determine the orientation of this header. The default is
            Qt.Horizontal.
        """
        super().__init__(orientation, parent)
        self.setHighlightSections(False)
        self.setSectionsClickable(False)
        self._section_clickable = True
        self.setSectionsMovable(sections_movable)
        self.sectionDoubleClicked.connect(self._handle_section_doubleclick)
        self.setSortIndicatorShown(False)
        self.hover = -1
        self.pressed = -1
        self.parent().model().sig_data_sorted.connect(self._update_sections)

    def mousePressEvent(self, e):
        """
        Override Qt method to save the logical index of the section that
        was pressed with the left button of the mouse.
        """
        if e.button() == Qt.LeftButton:
            self.pressed = self.logicalIndexAt(e.pos())
            self.parent().select_column_at(
                self.pressed,
                append=bool(e.modifiers() & Qt.ControlModifier),
                extend=bool(e.modifiers() & Qt.ShiftModifier)
                )
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        """
        Override Qt method to clear the pressed variable.
        """
        self.pressed = -1
        super().mouseReleaseEvent(e)

    def event(self, e):
        """
        Override Qt method to save the logical index of the section that
        is hovered by the bouse cursor.
        """
        if e.type() == QEvent.HoverEnter:
            self.hover = self.logicalIndexAt(e.pos())
        elif e.type() in [QEvent.Leave, QEvent.HoverLeave]:
            self.hover = -1
        elif e.type() == QEvent.HoverMove:
            self.hover = self.logicalIndexAt(e.pos())
        return super().event(e)

    def paintSection(self, painter, rect, logicalIndex):
        """
        Override Qt method to force the painting of the sort indicator
        on multiple columns.

        Based on the qt source code at:
        https://code.woboq.org/qt5/qtbase/src/widgets/itemviews/qheaderview.cpp.html
        """
        selected_columns = self.parent().get_selected_columns()
        state = QStyle.State_None
        if self.isEnabled():
            state |= QStyle.State_Enabled
        if self.window().isActiveWindow():
            state |= QStyle.State_Active
        if self._section_clickable:
            if logicalIndex == self.hover:
                state |= QStyle.State_MouseOver
            if logicalIndex == self.pressed:
                state |= QStyle.State_Sunken
                state |= QStyle.State_On
            else:
                sm = self.parent().selectionModel()
                if sm.columnIntersectsSelection(logicalIndex, QModelIndex()):
                    state |= QStyle.State_On
                if logicalIndex in selected_columns:
                    state |= QStyle.State_Sunken

        opt = QStyleOptionHeader()
        self.initStyleOption(opt)
        opt.rect = rect
        opt.section = logicalIndex
        opt.orientation = Qt.Horizontal
        opt.state |= state

        # Text options.
        text_alignment = self.model().headerData(
            logicalIndex, Qt.Horizontal, Qt.TextAlignmentRole)
        opt.textAlignment = (text_alignment if
                             text_alignment.isValid() else
                             Qt.AlignHCenter)

        opt.text = self.model().headerData(
            logicalIndex, Qt.Horizontal, Qt.DisplayRole)

        # Elide text.
        margin = 2 * self.style().pixelMetric(
            QStyle.PM_HeaderMargin, opt, self)
        text_rect = self.style().subElementRect(
            QStyle.SE_HeaderLabel, opt, self)
        opt.text = opt.fontMetrics.elidedText(
            opt.text, Qt.ElideRight, text_rect.width() - margin)

        # Sort indicator.
        sort_order = self.model().headerData(
            logicalIndex, Qt.Horizontal, Qt.InitialSortOrderRole)
        if sort_order is not None:
            opt.sortIndicator = (QStyleOptionHeader.SortDown if
                                 sort_order == 0 else
                                 QStyleOptionHeader.SortUp)

        # Section position.
        visual_index = self.visualIndex(logicalIndex)
        if visual_index != -1:
            first = self.logicalIndex(0) == logicalIndex
            last = (self.logicalIndex(
                self.visible_section_count() - 1) == logicalIndex)
            if first and last:
                opt.position = QStyleOptionHeader.OnlyOneSection
            elif first:
                opt.position = QStyleOptionHeader.Beginning
            elif last:
                opt.position = QStyleOptionHeader.End
            else:
                opt.position = QStyleOptionHeader.Middle

            # Selected position.
            previous_selected = (
                self.logicalIndex(visual_index - 1) in selected_columns)
            next_selected = (
                self.logicalIndex(visual_index + 1) in selected_columns)
            if previous_selected and next_selected:
                opt.selectedPosition = (
                    QStyleOptionHeader.NextAndPreviousAreSelected)
            elif previous_selected:
                opt.selectedPosition = QStyleOptionHeader.PreviousIsSelected
            elif next_selected:
                opt.selectedPosition = QStyleOptionHeader.NextIsSelected
            else:
                opt.selectedPosition = QStyleOptionHeader.NotAdjacent

        # Draw the section.
        self.style().drawControl(QStyle.CE_Header, opt, painter, self)

    # ---- Utils
    def sort_indicator_order(self):
        """
        Returns a list of the order for the sort indicator for the columns
        that have a sort indicator.
        """
        return self.model()._columns_sort_order

    def sort_indicator_sections(self):
        """
        Returns a list of the logical index of the sections that have a
        sort indicator
        """
        return self.model()._sort_by_columns

    def visible_section_count(self):
        """Return the number of visible sections."""
        return self.count() - self.hiddenSectionCount()

    def visual_rect_at(self, section):
        """
        Return the visual rect of the given section.
        """
        return QRect(self.sectionViewportPosition(section), 0,
                     self.sectionSize(section), self.size().height())

    # ---- Private methods
    @Slot(int)
    def _handle_section_doubleclick(self, section):
        """
        Sort data on the column that was double clicked with the mouse.
        """
        sort_order = self.model().headerData(
            section, Qt.Horizontal, Qt.InitialSortOrderRole)
        sort_order = (Qt.AscendingOrder if sort_order is None else
                      int(not bool(sort_order)))
        self.sig_sort_by_column.emit(section, sort_order)

    @Slot()
    def _update_sections(self):
        """"Update all sections of this header."""
        for section in range(self.count()):
            self.updateSection(section)


class SardesTableView(QTableView):
    """
    Sardes table view class to display and edit the data that are
    saved in the database.
    """
    sig_data_edited = Signal(object)
    sig_show_event = Signal()
    sig_data_updated = Signal()
    sig_rowcount_changed = Signal(object, int, int)

    def __init__(self, table_model, parent=None, multi_columns_sort=True,
                 sections_movable=True, sections_hidable=True,
                 disabled_actions=None):
        """
        Parameters
        ----------
        table_model : SardesSortFilterModel
            The sort filter proxy model that this table view is displaying.
        parent : QtWidgets.Widgets
            A Qt widget to be set as the parent of this table view.
        multi_columns_sort : bool, optional
            If multi_columns_sort is True, data are sortable by multiple
            columns, otherwise data can be sorted only by a single column.
        sections_movable : bool, optional
            If sections_movable is True, the header sections may be moved
            by the user, otherwise they are fixed in place.
            The default is True.
        sections_hidable : bool, optional
            If sections_hidable is True, columns can be hidden by the user,
            otherwise the columns cannot be hidden and are always visible.
        disabled_actions : list of str
            A list of strings corresponding to actions that should
            not be enabled in this table view Qt.Horizontal.
        """
        super().__init__(parent)
        self.setSortingEnabled(False)
        self.setAlternatingRowColors(False)
        self.setCornerButtonEnabled(True)
        self.setEditTriggers(self.DoubleClicked)
        self.setMouseTracking(True)
        self._sections_movable = sections_movable
        self._sections_hidable = sections_hidable
        self._disabled_actions = disabled_actions or []
        self._data_edit_cursor_pos = {}

        self._setup_table_model(table_model, multi_columns_sort)

        # Setup horizontal header.
        self.setHorizontalHeader(SardesHeaderView(
            self, sections_movable))
        self.horizontalHeader().sig_sort_by_column.connect(self.sort_by_column)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        # Setup actions and shortcuts.
        self._actions = {}
        self._setup_item_delegates()
        self._setup_shortcuts()

        # Connect update actions state slot to signals.
        self.selectionModel().currentChanged.connect(
            self._on_current_index_changed)
        self.sig_data_edited.connect(
            self._on_model_data_edit)
        self.sig_data_updated.connect(
            self._on_data_updated)
        self.selectionModel().selectionChanged.connect(
            self._on_selection_changed)

        # Make the connections required for _on_selected_rowcount_changed.
        self.model().rowsRemoved.connect(self._on_selected_rowcount_changed)
        self.model().rowsInserted.connect(self._on_selected_rowcount_changed)
        self.model().modelReset.connect(self._on_selected_rowcount_changed)
        self.selectionModel().selectionChanged.connect(
            self._on_selected_rowcount_changed)

        # List of QAction to toggle the visibility this table's columns.
        self._setup_column_visibility_actions()

    def showEvent(self, *args, **kargs):
        self.sig_show_event.emit()
        super().showEvent(*args, **kargs)

    def _setup_table_model(self, table_model, multi_columns_sort):
        """
        Setup the data model for this table view.
        """
        self.source_model = table_model
        self.source_model.sig_data_edited.connect(self.sig_data_edited.emit)
        self.source_model.sig_data_updated.connect(self.sig_data_updated.emit)
        self.source_model.sig_columns_mapper_changed.connect(
            self._setup_item_delegates)

        self.proxy_model = SardesSortFilterModel(
            self.source_model, multi_columns_sort)
        self.setModel(self.proxy_model)
        self.proxy_model.sig_data_sorted.connect(
            self.horizontalHeader().update)

    def _setup_item_delegates(self):
        """
        Setup the item delegates for each column of this table view.
        """
        for i, column in enumerate(self.model().columns):
            item_delegate = self.model().create_delegate_for_column(
                self, column)
            self.setItemDelegateForColumn(i, item_delegate)

    def _setup_column_visibility_actions(self):
        self._toggle_column_visibility_actions = []
        for i, label in enumerate(self.model().horizontal_header_labels):
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
        if 'io' not in self._disabled_actions:
            # Setup IO actions
            copy_to_clipboard_action = create_action(
                self, _("Copy"),
                icon='copy_clipboard',
                tip=_("Put a copy of the selection on the Clipboard "
                      "so you can paste it somewhere else."),
                triggered=self.copy_to_clipboard,
                shortcut='Ctrl+C',
                context=Qt.WidgetShortcut)
            self._actions['io'] = [copy_to_clipboard_action]
            self.addActions(self._actions['io'])

        # ---- Setup edit actions.
        self._actions['edit'] = []
        if 'edit_item' not in self._disabled_actions:
            self.edit_item_action = create_action(
                self, _("Edit"),
                icon='edit_database_item',
                tip=_("Edit the data of the currently focused cell."),
                triggered=self._edit_current_item,
                shortcut=['Enter', 'Return'],
                context=Qt.WidgetShortcut)
            self._actions['edit'].append(self.edit_item_action)
        if 'new_row' not in self._disabled_actions:
            new_row_action = create_action(
                self, _("New Item"),
                icon='add_row',
                tip=_("Create a new item."),
                triggered=self._add_new_row,
                shortcut=['Ctrl++', 'Ctrl+='],
                context=Qt.WidgetShortcut)
            self._actions['edit'].append(new_row_action)
        if 'delete_row' not in self._disabled_actions:
            self.delete_row_action = create_action(
                self, _("Delete Item"),
                icon='remove_row',
                tip=_("Delete selected items from the table."),
                triggered=self._delete_selected_rows,
                shortcut='Ctrl+-',
                context=Qt.WidgetShortcut)
            self._actions['edit'].append(self.delete_row_action)
        if 'clear_item' not in self._disabled_actions:
            self.clear_item_action = create_action(
                self, _("Clear"),
                icon='erase_data',
                tip=_("Set the currently focused item to NULL."),
                triggered=self._clear_current_item,
                shortcut='Delete',
                context=Qt.WidgetShortcut)
            self._actions['edit'].append(self.clear_item_action)
        if 'save_edits' not in self._disabled_actions:
            self.save_edits_action = create_action(
                self, _("Save edits"),
                icon='commit_changes',
                tip=_('Save all edits made to the table in the database.'),
                triggered=lambda: self._save_data_edits(force=False),
                shortcut=['Ctrl+Enter', 'Ctrl+Return'],
                context=Qt.WidgetShortcut)
            self.save_edits_action.setEnabled(False)
            self._actions['edit'].append(self.save_edits_action)
        if 'cancel_edits' not in self._disabled_actions:
            self.cancel_edits_action = create_action(
                self, _("Cancel edits"),
                icon='cancel_changes',
                tip=_('Cancel all edits made to the table since last save.'),
                triggered=self._cancel_data_edits,
                shortcut='Ctrl+Delete',
                context=Qt.WidgetShortcut)
            self.cancel_edits_action.setEnabled(False)
            self._actions['edit'].append(self.cancel_edits_action)
        if 'undo_edits' not in self._disabled_actions:
            self.undo_edits_action = create_action(
                self, _("Undo"),
                icon='undo',
                tip=_('Undo last edit made to the table.'),
                triggered=self._undo_last_data_edit,
                shortcut='Ctrl+Z',
                context=Qt.WidgetShortcut)
            self.undo_edits_action.setEnabled(False)
            self._actions['edit'].append(self.undo_edits_action)
        self.addActions(self._actions['edit'])

        # ---- Setup selection actions.
        if 'selection' not in self._disabled_actions:
            select_all_action = create_action(
                self, _("Select All"),
                icon='select_all',
                tip=_("Selects all items in the table."),
                triggered=self.select_all,
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
                      "all rows that intersect the selection will be "
                      "selected."),
                triggered=self.select_row,
                shortcut='Shift+Space',
                context=Qt.WidgetShortcut)

            select_column_action = create_action(
                self, _("Select Column"),
                icon='select_column',
                tip=_("Select the entire column of the current selection. "
                      "If the current selection spans multiple columns, all "
                      "columns that intersect the selection will "
                      "be selected."),
                triggered=self.select_column,
                shortcut='Ctrl+Space',
                context=Qt.WidgetShortcut)

            self._actions['selection'] = [
                select_all_action, select_clear_action, select_row_action,
                select_column_action]
            self.addActions(self._actions['selection'])
        if 'sort' not in self._disabled_actions:
            # Setup sort actions.
            sort_ascending_action = create_action(
                self, _("Sort Ascending"),
                icon='sort_ascending',
                tip=_("Reorder rows by sorting the data of the current column "
                      "in ascending order."),
                shortcut="Ctrl+<",
                context=Qt.WidgetShortcut,
                triggered=lambda _:
                    self.sort_by_current_column(Qt.AscendingOrder))

            sort_descending_action = create_action(
                self, _("Sort Descending"),
                icon='sort_descending',
                tip=_("Reorder rows by sorting the data of the current column "
                      "in descending order."),
                shortcut="Ctrl+>",
                context=Qt.WidgetShortcut,
                triggered=lambda _:
                    self.sort_by_current_column(Qt.DescendingOrder))

            sort_clear_action = create_action(
                self, _("Clear Sort"),
                icon='sort_clear',
                tip=_("Clear all sorts applied to the columns of the table."),
                triggered=lambda _: self.clear_sort(),
                shortcut="Ctrl+.",
                context=Qt.WidgetShortcut)

            self._actions['sort'] = [sort_ascending_action,
                                     sort_descending_action,
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

    def _on_data_updated(self):
        """
        Handle when the data of this table view was changed.
        """
        self._on_model_data_edit(None)

    def _on_current_index_changed(self):
        """
        Handle when the current position of this table view cursor changes.
        """
        self._update_actions_state()

    def _on_selection_changed(self):
        """
        Handle when the list of selected indexes in the table changes.
        """
        self._update_actions_state()

    def _on_model_data_edit(self, data_edit):
        """
        Handle when an edit is made to the data of the table model.
        """
        if data_edit is not None:
            if data_edit.id in self._data_edit_cursor_pos:
                # This mean that the given data edit was just undone.
                del self._data_edit_cursor_pos[data_edit.id]
            else:
                if data_edit.type() == SardesTableModelBase.RowAdded:
                    model_index = self.model().index(
                        self.model().rowCount() - 1, 0)
                    self.setCurrentIndex(model_index)
                    self._ensure_visible(model_index)

                # Save the cursor position for that edit.
                current_source_index = self.model().mapToSource(
                    self.selectionModel().currentIndex())
                self._data_edit_cursor_pos[data_edit.id] = (
                    current_source_index.row(), current_source_index.column())
        else:
            self._data_edit_cursor_pos = {}
        self._update_actions_state()

    def _update_actions_state(self):
        """
        Update the states of this tableview actions.
        """
        current_index = self.selectionModel().currentIndex()
        if current_index.isValid():
            is_required = self.is_data_required_at(current_index)
            is_null = self.model().is_null(current_index)
            is_editable = self.is_data_editable_at(current_index)
            if 'clear_item' not in self._disabled_actions:
                self.clear_item_action.setEnabled(
                    not is_required and not is_null and is_editable)
            if 'edit_item' not in self._disabled_actions:
                self.edit_item_action.setEnabled(is_editable)

        has_unsaved_data_edits = self.model().has_unsaved_data_edits()
        is_data_edit_count = bool(self.model().data_edit_count())
        if 'save_edits' not in self._disabled_actions:
            self.save_edits_action.setEnabled(has_unsaved_data_edits)
        if 'undo_edits' not in self._disabled_actions:
            self.undo_edits_action.setEnabled(is_data_edit_count)
        if 'cancel_edits' not in self._disabled_actions:
            self.cancel_edits_action.setEnabled(has_unsaved_data_edits)

    def _on_selected_rowcount_changed(self):
        """
        Handle when the number of selected rows or the number of visibles
        rows changed.
        """
        self.sig_rowcount_changed.emit(
            self, self.selected_row_count(), self.visible_row_count())

    # ---- Options
    @property
    def sections_hidable(self):
        """
        Return wheter it is possible to hide sections.
        """
        return self._sections_hidable

    @property
    def confirm_before_saving_edits(self):
        """
        Return wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        if self.model().db_connection_manager is not None:
            return (self.model().db_connection_manager
                    ._confirm_before_saving_edits)
        else:
            return self._confirm_before_saving_edits

    @confirm_before_saving_edits.setter
    def confirm_before_saving_edits(self, x):
        """
        Set wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        self._confirm_before_saving_edits = bool(x)
        if self.model().db_connection_manager is not None:
            (self.model().db_connection_manager
             ._confirm_before_saving_edits) = bool(x)

    # ---- Sorting
    def clear_sort(self):
        """
        Clear all sorts applied to the columns of this table.
        """
        self.model().sort(-1, -1)

    def sort_by_column(self, column_logical_index, sorting_order):
        """
        Sort the rows of this table by ordering the data of the specified
        column in the specified sorting order.

        Parameters
        ----------
        column_logical_index : int
            The logical index of the column by which to sort the data of the
            whole table.
        sorting_order : int
            An integer to indicate how the data in the table needs to be
            sorted according to the specified column. 0 is used for ascending
            sorting, 1 for descending sorting, and -1 for no sorting.
        """
        self.model().sort(column_logical_index, sorting_order)

    def sort_by_current_column(self, sorting_order):
        """
        Sort the rows of this table by ordering the data of the currently
        selected column, if any, in the specified sorting order.

        Parameters
        ----------
        sorting_order : int
            An integer to indicate how the data in the table needs to be
            sorted according to the current column if any. 0 is used for
            ascending sorting, 1 for descending sorting, and -1 for no sorting.
        """
        self.sort_by_column(
            self.selectionModel().currentIndex().column(), sorting_order)

    # ---- Data selection
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

    def select_all(self):
        """
        Selects all items in this table view.
        """
        self.setFocus()
        self.selectAll()

    def select_row(self):
        """
        Select the entire row of the current selection. If the current
        selection spans multiple rows, all rows that intersect the selection
        will be selected.
        """
        self.setFocus()
        rows_to_select = self.get_rows_intersecting_selection()
        for interval in intervals_extract(rows_to_select):
            self.selectionModel().select(
                QItemSelection(self.model().index(interval[0], 0),
                               self.model().index(interval[1], 0)),
                QItemSelectionModel.Select | QItemSelectionModel.Rows)

    def get_rows_intersecting_selection(self):
        """
        Return the list of rows intersecting selection.
        """
        rows = []
        for index_range in self.selectionModel().selection():
            if index_range.isValid():
                rows.extend(range(index_range.top(), index_range.bottom() + 1))
        return [*{*rows}]

    def select_column_at(self, column, append=False, extend=False):
        """
        Select all item in the given column. If extend is True, all items
        between the current column and given column will be selected.
        If append is True, the current selection is cleared before
        selecting new items.
        """
        current_column = self.selectionModel().currentIndex().column()
        if append is False:
            self.selectionModel().clear()
        if extend:
            current_visual_column = (
                self.horizontalHeader().visualIndex(current_column))
            visual_column = self.horizontalHeader().visualIndex(column)

            selected_columns = sorted([
                self.horizontalHeader().logicalIndex(column) for
                column in range(min(current_visual_column, visual_column),
                                max(current_visual_column, visual_column) + 1)
                ])
            for interval in intervals_extract(selected_columns):
                self.selectionModel().select(
                    QItemSelection(self.model().index(0, interval[0]),
                                   self.model().index(0, interval[1])),
                    QItemSelectionModel.Select | QItemSelectionModel.Columns
                    )
        else:
            self.selectionModel().select(
                QItemSelection(self.model().index(0, column),
                               self.model().index(0, column)),
                QItemSelectionModel.Select | QItemSelectionModel.Columns
                )
        self.selectionModel().setCurrentIndex(
            self.model().index(0, column), QItemSelectionModel.Current)

    def get_columns_intersecting_selection(self):
        """
        Return the list of columns intersecting selection.
        """
        columns = []
        for index_range in self.selectionModel().selection():
            if index_range.isValid():
                columns.extend(range(
                    index_range.left(), index_range.right() + 1))
        return [*{*columns}]

    def select_column(self):
        """
        Select the entire column of the current selection. If the current
        selection spans multiple columns, all columns that intersect the
        selection will be selected.
        """
        self.setFocus()
        selected_columns = sorted(self.get_columns_intersecting_selection())
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
        if self.row_count() == 0:
            return []
        else:
            row_count = np.zeros(self.model().columnCount())
            for index_range in self.selectionModel().selection():
                if not index_range.isValid():
                    continue
                columns = [column for column in
                           range(index_range.left(), index_range.right() + 1)]
                row_count[columns] += len(
                    range(index_range.top(), index_range.bottom() + 1))
            return np.where(row_count == self.row_count())[0].tolist()

    def get_selected_count(self):
        """
        Return the number of cells that are currently selected in the table.

        Note that the approach used here is a lot more fast and efficient then
        using 'len(self.selectionModel().selectedIndexes())', which can take
        several seconds for big tables.
        """
        selected_count = 0
        for index_range in self.selectionModel().selection():
            selected_count += (
                (index_range.right() - index_range.left() + 1) *
                (index_range.bottom() - index_range.top() + 1))
        return selected_count

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
        selected_count = self.get_selected_count()
        if selected_count == 0:
            return

        selected_columns = sorted(
            self.get_columns_intersecting_selection(),
            key=lambda v: self.horizontalHeader().visualIndex(v))
        selected_rows = sorted(self.get_rows_intersecting_selection())
        if len(selected_columns) * len(selected_rows) != selected_count:
            QMessageBox.information(
                self, __appname__,
                _("This function cannot be used with multiple selections."),
                buttons=QMessageBox.Ok)
        else:
            selected_data = self.model().visual_dataf.iloc[
                self.model().mapRowToSource(selected_rows), selected_columns]
            selected_data.rename(
                self.model()._data_columns_mapper,
                axis='columns',
                inplace=True)
            selected_data.to_clipboard(excel=True, index=False, na_rep='')

    def row_count(self):
        """Return this table number of visible row."""
        return self.model().rowCount()

    def selected_row_count(self):
        """
        Return the number of rows of this table that have at least one
        selected items.
        """
        return len(self.get_rows_intersecting_selection())

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
        return self.horizontalHeader().visible_section_count()

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
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setSectionsClickable(False)
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
        try:
            return self.itemDelegate(model_index).is_editable
        except AttributeError:
            return False

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
            if not len(self._actions[section]):
                continue
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
            self.itemDelegate(current_index).clear_model_data_at(current_index)

    def _edit_current_item(self):
        """
        Turn on edit mode for this table current cell.
        """
        current_index = self.selectionModel().currentIndex()
        if current_index.isValid():
            if self.state() != self.EditingState:
                self.edit(current_index)
            else:
                self.itemDelegate(current_index).commit_data()

    def _cancel_data_edits(self):
        """
        Cancel all the edits that were made to the table data of this view
        since last save.
        """
        self.model().cancel_data_edits()

    def _undo_last_data_edit(self):
        """
        Undo the last data edits that was added to the table.
        """
        last_edit = self.model().data_edits()[-1]
        last_edit_cursor_pos = self._data_edit_cursor_pos[last_edit.id]
        if last_edit.type() == SardesTableModelBase.RowAdded:
            row, col = self._data_edit_cursor_pos[last_edit.id]
            added_row = self.model().mapFromSource(
                self.model().sourceModel().index(*last_edit_cursor_pos)
                ).row()
            self.model().undo_last_data_edit()

            # Since the model index corresponding to the added row doesn't
            # exist once the operation is undone, we need to select the
            # index just above or below that index in the proxy model.
            model_index = self.model().index(max(added_row - 1, 0), 0)
        else:
            self.model().undo_last_data_edit()
            model_index = self.model().mapFromSource(
                self.model().sourceModel().index(*last_edit_cursor_pos))

        self.selectionModel().clearSelection()
        self._ensure_visible(model_index)
        self.selectionModel().setCurrentIndex(
            model_index, self.selectionModel().NoUpdate)

    def _save_data_edits(self, force=True):
        """
        Save the data edits to the database. If 'force' is 'False', a message
        is first shown before proceeding.
        """
        if force is False and self.confirm_before_saving_edits:
            msgbox = QMessageBox(
                QMessageBox.Warning,
                _('Save changes'),
                _("This will permanently save the changes made in this "
                  "table in the database.<br><br>"
                  "This action <b>cannot</b> be undone.<br><br>"),
                buttons=QMessageBox.Save | QMessageBox.Cancel,
                parent=self)
            msgbox.button(msgbox.Save).setText(_("Save"))
            msgbox.button(msgbox.Cancel).setText(_("Cancel"))

            chkbox = QCheckBox(
                _("Do not show this message again during this session."))
            msgbox.setCheckBox(chkbox)

            reply = msgbox.exec_()
            if reply == QMessageBox.Cancel:
                return
            else:
                self.confirm_before_saving_edits = not chkbox.isChecked()

        self.selectionModel().clearSelection()
        self.model().save_data_edits()

    def _add_new_row(self):
        """
        Add a new empty row at the end of this table.
        """
        self.model().add_new_row()

    def _delete_selected_rows(self):
        """Delete rows from the table with selected indexes"""
        self.model().delete_row(self.get_rows_intersecting_selection())

    def _ensure_visible(self, model_index):
        """
        Scroll to the item located at the given model index if it is not
        currently visible in the scrollarea.
        """
        item_rect = self.visualRect(model_index)
        view_rect = self.geometry()
        if not view_rect.contains(item_rect):
            self.scrollTo(model_index, hint=self.PositionAtCenter)

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
        if trigger is None or trigger == self.DoubleClicked:
            # We clear all selected items but the current index.
            self.selectionModel().setCurrentIndex(
                model_index, self.selectionModel().ClearAndSelect)
        if trigger is None:
            # We clear all selected items but the current index.
            self.selectionModel().setCurrentIndex(
                model_index, self.selectionModel().ClearAndSelect)

            # Scroll to item if it is not currently visible in the scrollarea.
            item_rect = self.visualRect(model_index)
            view_rect = self.geometry()
            if not view_rect.contains(item_rect):
                self.scrollTo(model_index, hint=self.EnsureVisible)
            return super().edit(model_index)
        else:
            return super().edit(model_index, trigger, event)


class SardesTableWidget(SardesPaneWidget):
    EDIT_ACTIONS = ['edit_item', 'new_row', 'delete_row', 'clear_item',
                    'save_edits', 'cancel_edits', 'undo_edits']

    def __init__(self, table_model, parent=None, multi_columns_sort=True,
                 sections_movable=True, sections_hidable=True,
                 disabled_actions=None, statusbar=False):
        """
        Parameters
        ----------
        table_model : SardesTableModel
            The source model that we want to display in the tableview of this
            table widget.
        parent : QtWidgets.Widgets
            A Qt widget to be set as the parent of this table view.
        multi_columns_sort : bool, optional
            If multi_columns_sort is True, data are sortable by multiple
            columns, otherwise data can be sorted only by a single column.
        sections_movable : bool, optional
            If sections_movable is True, the header sections may be moved
            by the user, otherwise they are fixed in place.
            The default is True.
        sections_hidable : bool, optional
            If sections_hidable is True, columns can be hidden by the user,
            otherwise the columns cannot be hidden and are always visible.
        disabled_actions : list of str
            A list of strings corresponding to a group of actions that should
            not be enabled in the view of this table widget.
            Qt.Horizontal.
        """
        super().__init__(parent)
        self.setAutoFillBackground(True)

        self.tableview = SardesTableView(
            table_model, self, multi_columns_sort, sections_movable,
            sections_hidable, disabled_actions)
        self.tableview.setAutoFillBackground(True)
        self.tableview.viewport().setStyleSheet(
            "background-color: rgb(%d, %d, %d);" %
            getattr(QStyleOption().palette, 'light')().color().getRgb()[:-1])

        self.progressbar = ProcessStatusBar(self, 96, 16, Qt.Vertical)
        self._end_process_timer = QTimer(self)
        self._end_process_timer.setSingleShot(True)
        self._end_process_timer.timeout.connect(self._end_process)
        self._end_process_timer._status_message = None

        self.model().sig_data_about_to_be_updated.connect(
            lambda: self._start_process(None))
        self.model().sig_data_updated.connect(
            lambda: self._handle_process_ended(None))
        self.model().sig_data_about_to_be_saved.connect(
            lambda: self._start_process(_('Saving edits in the database...')))
        self.model().sig_data_saved.connect(
            lambda: self._handle_process_ended(
                _('Edits saved sucessfully in the database.')))

        progressbar_layout = QGridLayout()
        progressbar_layout.setContentsMargins(0, 0, 0, 0)
        progressbar_layout.addWidget(self.progressbar, 1, 1)
        progressbar_layout.setRowStretch(0, 1)
        progressbar_layout.setRowStretch(2, 1)
        progressbar_layout.setColumnStretch(0, 1)
        progressbar_layout.setColumnStretch(2, 1)

        self.message_layout = QVBoxLayout()
        self.message_layout.setContentsMargins(0, 0, 0, 0)

        self.central_widget = QWidget()
        central_widget_layout = QGridLayout(self.central_widget)
        central_widget_layout.setContentsMargins(0, 0, 0, 0)
        central_widget_layout.addLayout(self.message_layout, 0, 0)
        central_widget_layout.addWidget(self.tableview, 1, 0)
        central_widget_layout.addLayout(progressbar_layout, 1, 0)
        central_widget_layout.setRowStretch(1, 1)
        central_widget_layout.setColumnStretch(0, 1)
        central_widget_layout.setSpacing(0)
        self.set_central_widget(self.central_widget)

        self._setup_upper_toolbar()

        self.statusbar = None
        self.rowcount_label = None
        if statusbar is True:
            self._setup_status_bar()

    # ---- Layout
    def install_message_box(self, message_box):
        """
        Add the given message box to this table widget.
        """
        self.message_layout.addWidget(message_box)
        message_box.hide()
        return message_box

    # ---- Public methods
    def clear_model_data(self):
        """
        Clear the data of this table widget's model.
        """
        self.model().clear_data()

    @property
    def db_connection_manager(self):
        """
        Return the database connection manager associated with the model
        of this table widget.
        """
        return self.model().db_connection_manager

    def get_table_title(self):
        """Return the title of this widget's table."""
        return self.tableview.source_model._table_title

    def get_table_id(self):
        """Return the ID of this widget's table."""
        return self.tableview.source_model._table_id

    def model(self):
        """
        Return the model associated with this table widget.
        """
        return self.tableview.model()

    def update_model_data(self):
        """
        Fetch the data from the database and update the model's data and
        library of this table widget.
        """
        return self.model().update_data()

    # ---- Setup
    def eventFilter(self, widget, event):
        """
        An event filter to prevent status tips from buttons and menus
        to show in the status bar of the table.
        """
        if event.type() == QEvent.StatusTip:
            return True
        return False

    def _setup_upper_toolbar(self):
        """
        Setup the upper toolbar of this table widget.
        """
        super()._setup_upper_toolbar()
        toolbar = self.get_upper_toolbar()

        sections = list(self.tableview._actions.keys())
        for section in sections:
            actions = self.tableview._actions[section]
            if not len(actions):
                continue
            for action in self.tableview._actions[section]:
                toolbar.addAction(action)
            if section != sections[-1]:
                toolbar.addSeparator()

        if self.sections_hidable:
            # We add a stretcher here so that the columns options button is
            # aligned to the right side of the toolbar.
            self._upper_toolbar_separator = toolbar.addWidget(
                create_toolbar_stretcher())

            columns_options_action = toolbar.addWidget(
                self._create_columns_options_button())
            columns_options_action.setVisible(self.sections_hidable)
        else:
            self._upper_toolbar_separator = None

    def _setup_status_bar(self):
        """
        Setup the status bar of this table widget.
        """
        self.statusbar = self.statusBar()
        self.statusbar.setSizeGripEnabled(False)
        self.installEventFilter(self)

        # Number of row(s) selected.
        self.rowcount_label = RowCountLabel()
        self.statusbar.addPermanentWidget(self.rowcount_label)
        self.rowcount_label.register_table(self.tableview)

    # ---- Toolbar
    def add_toolbar_widget(self, widget, which='upper'):
        """
        Add a new widget to the uppermost toolbar if 'which' is 'upper',
        else add it to the lowermost toolbar.
        """
        if which == 'upper':
            if self._upper_toolbar_separator is None:
                self.get_upper_toolbar().addWidget(widget)
            else:
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
            if self._upper_toolbar_separator is None:
                self.get_upper_toolbar().addSeparator()
            else:
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

    def get_columns_sorting_state(self):
        """
        Return the list of column names and the list of corresponding
        sort orders (0 for ascending, 1 for descending) by which the data
        were sorted in the model of this table widget.
        """
        return self.model().get_columns_sorting_state()

    def set_columns_sorting_state(self, sort_by_columns, columns_sort_order):
        """
        Set the list of column names and the list of corresponding
        sort orders (0 for ascending, 1 for descending) by which the data
        need to be sorted in the model of this table widget.
        """
        self.model().set_columns_sorting_state(
            sort_by_columns, columns_sort_order)

    # ---- Columns option toolbutton
    @property
    def sections_hidable(self):
        """
        Return wheter it is possible to hide sections of the tableview.
        """
        return self.tableview.sections_hidable

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

    # ---- Process state
    def _start_process(self, text=''):
        if text is not None and self.statusbar is not None:
            self.statusBar().showMessage(text)
        self._end_process_timer.stop()
        self.get_upper_toolbar().setEnabled(False)
        self.tableview.setEnabled(False)
        self.progressbar.show()

    def _handle_process_ended(self, text=None):
        if text is not None:
            self._end_process_timer._status_message = text
        self._end_process_timer.start(MSEC_MIN_PROGRESS_DISPLAY)

    def _end_process(self, text=None):
        if text is not None and self.statusbar is not None:
            self.statusBar().showMessage(text)
        if self._end_process_timer._status_message is not None:
            if self.statusbar is not None:
                self.statusBar().showMessage(
                    self._end_process_timer._status_message)
            self._end_process_timer._status_message = None
        self.get_upper_toolbar().setEnabled(True)
        self.tableview.setEnabled(True)
        self.tableview.setFocus()
        self.progressbar.hide()


class SardesStackedTableWidget(SardesPaneWidget):
    """
    A SardesPaneWidget to display multiple SardesTableWidget in a tab widget.
    """

    def __init__(self, parent=None, tabs_closable=False, tabs_movable=False):
        super().__init__(parent)
        self._setup_status_bar()

        self.tabwidget = QTabWidget(self)
        self.tabwidget.setTabPosition(QTabWidget.North)
        self.tabwidget.setIconSize(QSize(18, 18))
        self.tabwidget.setTabsClosable(tabs_closable)
        self.tabwidget.setMovable(tabs_movable)
        self.tabwidget.currentChanged.connect(self._on_current_changed)
        self.tabwidget.setStyleSheet("QTabWidget::pane {padding: 0px;}")

        self.tabbar = self.tabwidget.tabBar()

        self.tabbar.installEventFilter(self)
        self.tabwidget.installEventFilter(self)
        self.installEventFilter(self)
        self.tabwidget.tabCloseRequested.connect(self.close_table_at)

        self.set_central_widget(self.tabwidget)

    # ---- Public interface
    def add_table(self, table, title, switch_to_table=False):
        """
        Add the given table to this stacked table widget.
        """
        self.tabwidget.addTab(table, get_icon('table'), title)
        self.rowcount_label.register_table(table.tableview)

        toolbar = table.get_upper_toolbar()
        table.removeToolBar(toolbar)
        self.addToolBar(table.get_upper_toolbar())
        self._on_current_changed(self.currentIndex())

        table.tableview.sig_data_edited.connect(self._update_tab_names)
        table.tableview.sig_data_updated.connect(self._update_tab_names)

        if switch_to_table:
            self.tabwidget.setCurrentWidget(table)
            table.tableview.setFocus()

    def close_table_at(self, index):
        """
        Close the table at the given tabwidget index.
        """
        table = self.tabwidget.widget(index)
        self.removeToolBar(table.get_upper_toolbar())
        table.tableview.close()
        table.close()
        self.tabwidget.removeTab(index)
        self.focus_current_table()

    def close_all_tables(self):
        """Close all opened table."""
        for index in reversed(range(self.count())):
            self.close_table_at(index)

    def focus_current_table(self):
        """
        Set the focus to the current table if it exists.
        """
        try:
            self.tabwidget.currentWidget().tableview.setFocus()
        except AttributeError:
            # This means the stacked table widget is empty.
            pass

    # ---- Private interface
    def _setup_status_bar(self):
        """
        Setup the status bar of this table widget.
        """
        statusbar = self.statusBar()
        statusbar.setSizeGripEnabled(False)

        # Add number of row(s) selected.
        self.rowcount_label = RowCountLabel()
        statusbar.addPermanentWidget(self.rowcount_label)

    def _update_tab_names(self):
        """
        Append a '*' symbol at the end of a tab name when its corresponding
        table have unsaved edits.
        """
        for index in range(self.count()):
            table = self.tabwidget.widget(index)
            tab_text = table.get_table_title()
            if table.tableview.model().has_unsaved_data_edits():
                tab_text += '*'
            self.tabwidget.setTabText(index, tab_text)

    def _on_current_changed(self, current_index):
        """
        Handle when the current index of this stacked table widget changed.
        """
        for index in range(self.count()):
            self.tabwidget.widget(index).get_upper_toolbar().setVisible(
                index == current_index)
        self.focus_current_table()

    # ---- Qt method overrides
    def eventFilter(self, widget, event):
        if event.type() == QEvent.MouseButtonPress:
            self.focus_current_table()
        elif event.type() == QEvent.StatusTip:
            # Prevent status tips from buttons and menus to show in the
            # status bar of this stacked table widget.
            return True
        return super().eventFilter(widget, event)

    # ---- QTabWidget public API
    def count(self):
        return self.tabwidget.count()

    def currentWidget(self):
        return self.tabwidget.currentWidget()

    def currentIndex(self):
        return self.tabwidget.currentIndex()

    def setCurrentIndex(self, *args, **kargs):
        return self.tabwidget.setCurrentIndex(*args, **kargs)

    def setCurrentWidget(self, *args, **kargs):
        return self.tabwidget.setCurrentWidget(*args, **kargs)

    @property
    def tabCloseRequested(self):
        return self.tabwidget.tabCloseRequested

    def tabText(self, *args, **kargs):
        return self.tabwidget.tabText(*args, **kargs)

    def widget(self, *args, **kargs):
        return self.tabwidget.widget(*args, **kargs)


if __name__ == '__main__':
    from sardes.database.database_manager import DatabaseConnectionManager
    app = QApplication(sys.argv)

    manager = DatabaseConnectionManager()
    table_view = SardesTableView(manager)
    table_view.show()
    manager.connect_to_db('debug')

    sys.exit(app.exec_())
