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

# ---- Third party imports
import numpy as np
import pandas as pd
from qtpy.QtCore import (QEvent, Qt, Signal, Slot, QItemSelection, QSize,
                         QItemSelectionModel, QRect, QTimer, QModelIndex,)
from qtpy.QtGui import QCursor, QBrush, QPalette, QColor
from qtpy.QtWidgets import (
    QApplication, QCheckBox,
    QHeaderView, QLabel, QMenu, QMessageBox, QTableView, QStyle, QStyleOption,
    QWidget, QGridLayout, QStyleOptionHeader, QVBoxLayout, QTabWidget)

# ---- Local imports
from sardes import __appname__
from sardes.api.panes import SardesPaneWidget
from sardes.api.tablemodels import SardesSortFilterModel, SardesTableModelBase
from sardes.api.tools import SardesTool
from sardes.config.icons import get_icon
from sardes.config.locale import _
from sardes.config.gui import get_iconsize
from sardes.utils.data_operations import intervals_extract
from sardes.utils.qthelpers import (
    create_action, create_toolbutton, create_toolbar_stretcher,
    qbytearray_to_hexstate, hexstate_to_qbytearray)
from sardes.widgets.statusbar import ProcessStatusBar

# Define the minimum amount of time that the tables wait spinner are shown.
# Otherwise, for very short process, it only flashes in the screen.
MSEC_MIN_PROGRESS_DISPLAY = 500


# =============================================================================
# ---- Tools
# =============================================================================
class ImportFromClipboardTool(SardesTool):
    """
    A tool to append the Clipboard contents to a Sardes table widget.
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            name='import_from_clipboard',
            text=_('Import from Clipboard'),
            icon='import_clipboard',
            tip=_('Add the Clipboard contents to this table.')
            )

    def __triggered__(self):
        new_data = pd.read_clipboard(sep='\t', dtype='str', header=None)
        if new_data.empty:
            self.parent.show_message(
                title=_("Warning"),
                message=_("Nothing was added to the table because the "
                          "Clipboard was empty."),
                func='warning')
            return

        table_visible_columns = self.parent.tableview.visible_columns()
        if len(new_data.columns) > len(table_visible_columns):
            self.parent.show_message(
                title=_("Warning"),
                message=_("The Clipboard contents cannot be added to "
                          "the table because the number of columns of the "
                          "copied data is too large."),
                func='warning')
            return

        column_names_headers_map = (
            self.parent.model().column_names_headers_map())
        table_visible_labels = [
            column_names_headers_map[column].lower().replace(' ', '')
            for column in table_visible_columns]

        new_data_columns = []
        for i in range(len(new_data.columns)):
            new_data_i = (
                '' if pd.isnull(new_data.iat[0, i]) else new_data.iat[0, i]
                ).lower().replace(' ', '')
            if new_data_i in table_visible_columns:
                new_data_columns.append(new_data_i)
            elif new_data_i in table_visible_labels:
                index = table_visible_labels.index(new_data_i)
                new_data_columns.append(table_visible_columns[index])
            else:
                break
        if len(new_data.columns) == len(set(new_data_columns)):
            # This means that the headers were correctly provided in
            # the copied data. We then need to drop the first row of the data.
            new_data.drop(new_data.index[0], axis='index', inplace=True)
        else:
            # This means that there was a problem reading one or more column
            # names, that  or
            # that the columns names were not provided with the imported data.
            new_data_columns = table_visible_columns[:len(new_data.columns)]
        new_data.columns = new_data_columns

        warning_messages = []
        for column in new_data.columns:
            delegate = self.parent.tableview.itemDelegateForColumn(
                self.parent.model().column_names().index(column))
            new_data[column], warning_message = delegate.format_data(
                new_data[column])
            if warning_message is not None:
                warning_messages.append(warning_message)

        formatted_message = None
        if new_data.isnull().values.flatten().all():
            formatted_message = _(
                "Nothing was added to the table because the Clipboard "
                "did not contain any valid data.")
            if new_data.size > 1 and len(warning_messages):
                formatted_message += "<br><br>"
                formatted_message += _(
                    "The following error(s) occurred while trying to add the "
                    "Clipboard contents to this table:")
                formatted_message += (
                    '<ul style="margin-left:-30px"><li>{}.</li></ul>'.format(
                        ';</li><li>'.join(warning_messages)))
        else:
            values = new_data.to_dict(orient='records')
            self.parent.tableview._append_row(values)
            if len(warning_messages):
                formatted_message = _(
                    "The following error(s) occurred while adding the "
                    "Clipboard contents to this table:")
                formatted_message += (
                    '<ul style="margin-left:-30px"><li>{}.</li></ul>'.format(
                        ';</li><li>'.join(warning_messages)))
        if formatted_message is not None:
            self.parent.show_message(
                title=_("Warning"),
                message=formatted_message,
                func='warning')


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
        text = _("{} out of {} row(s) selected").format(
            selected_row_count, visible_row_count)
        self.setText(text + " ")

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
        self.setMinimumSectionSize(self._minimum_section_size())

    def restoreState(self, state):
        """
        Override Qt method to enforce sections minimum size.
        """
        super().restoreState(state)
        self.setMinimumSectionSize(self._minimum_section_size())

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

        margin = 2 * self.style().pixelMetric(
            QStyle.PM_HeaderMargin, opt, self)

        # Icon options.
        if not self.model().columns()[logicalIndex].editable:
            opt.iconAlignment = Qt.AlignVCenter
            opt.icon = get_icon('table_column_lock')
            margin += (
                self.style().pixelMetric(QStyle.PM_SmallIconSize, opt, self) +
                self.style().pixelMetric(QStyle.PM_HeaderMargin, opt, self))

        # Text options.
        text_alignment = self.model().headerData(
            logicalIndex, Qt.Horizontal, Qt.TextAlignmentRole)
        opt.textAlignment = (text_alignment if
                             text_alignment.isValid() else
                             Qt.AlignHCenter)

        opt.text = self.model().headerData(
            logicalIndex, Qt.Horizontal, Qt.DisplayRole)

        foreground_color = self.model().headerData(
            logicalIndex, Qt.Horizontal, Qt.ForegroundRole)
        if foreground_color.isValid():
            opt.palette.setBrush(QPalette.ButtonText, QBrush(foreground_color))

        # Elide text.
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
    def _minimum_section_size(self):
        """
        Calcul a minimum section size to include the width of the braces '[]'
        enclosing the titles of columns that are not editable.

        Based on the qt 'minimumSectionSize' source code at:
        https://code.woboq.org/qt5/qtbase/src/widgets/itemviews/qheaderview.cpp.html
        """
        strut = QApplication.globalStrut()
        margin = self.style().pixelMetric(
            QStyle.PM_HeaderMargin, None, self)
        icon_size = self.style().pixelMetric(
            QStyle.PM_SmallIconSize, None, self)
        fm = self.fontMetrics()
        return max(strut.width(), fm.maxWidth() + 3 * margin + icon_size)

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
    sig_rows_deleted = Signal(list)
    sig_current_changed = Signal(object)
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
        self.model().dataChanged.connect(self._on_selected_rowcount_changed)
        self.selectionModel().selectionChanged.connect(
            self._on_selected_rowcount_changed)

        # List of QAction to toggle the visibility this table's columns.
        self._setup_column_visibility_actions()

    def showEvent(self, *args, **kargs):
        self.sig_show_event.emit()
        super().showEvent(*args, **kargs)

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
        for i, column in enumerate(self.model().columns()):
            item_delegate = self.model().create_delegate_for_column(
                self, column)
            self.setItemDelegateForColumn(i, item_delegate)

    def _setup_column_visibility_actions(self):
        self._toggle_column_visibility_actions = []
        for i, label in enumerate(self.model().column_headers()):
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
                context=Qt.WidgetShortcut,
                name='copy_to_clipboard')
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
                context=Qt.WidgetShortcut,
                name='edit_item')
            self._actions['edit'].append(self.edit_item_action)
        if 'new_row' not in self._disabled_actions:
            self.new_row_action = create_action(
                self, _("New Item"),
                icon='add_row',
                tip=_("Create a new item."),
                triggered=self._add_new_row,
                shortcut=['Ctrl++', 'Ctrl+='],
                context=Qt.WidgetShortcut,
                name='new_row')
            self._actions['edit'].append(self.new_row_action)
        if 'delete_row' not in self._disabled_actions:
            self.delete_row_action = create_action(
                self, _("Delete Item"),
                icon='remove_row',
                tip=_("Delete selected items from the table."),
                triggered=self._delete_selected_rows,
                shortcut='Ctrl+-',
                context=Qt.WidgetShortcut,
                name='delete_row')
            self._actions['edit'].append(self.delete_row_action)
        if 'clear_item' not in self._disabled_actions:
            self.clear_item_action = create_action(
                self, _("Clear"),
                icon='erase_data',
                tip=_("Set the currently focused item to NULL."),
                triggered=self._clear_current_item,
                shortcut='Delete',
                context=Qt.WidgetShortcut,
                name='clear_item')
            self._actions['edit'].append(self.clear_item_action)
        if 'save_edits' not in self._disabled_actions:
            self.save_edits_action = create_action(
                self, _("Save edits"),
                icon='commit_changes',
                tip=_('Save all edits made to the table in the database.'),
                triggered=self._check_data_edits,
                shortcut=['Ctrl+Enter', 'Ctrl+Return'],
                context=Qt.WidgetShortcut,
                name='sav_edits')
            self.save_edits_action.setEnabled(False)
            self._actions['edit'].append(self.save_edits_action)
        if 'cancel_edits' not in self._disabled_actions:
            self.cancel_edits_action = create_action(
                self, _("Cancel edits"),
                icon='cancel_changes',
                tip=_('Cancel all edits made to the table since last save.'),
                triggered=self._cancel_data_edits,
                shortcut='Ctrl+Delete',
                context=Qt.WidgetShortcut,
                name='cancel_edits')
            self.cancel_edits_action.setEnabled(False)
            self._actions['edit'].append(self.cancel_edits_action)
        if 'undo_edits' not in self._disabled_actions:
            self.undo_edits_action = create_action(
                self, _("Undo"),
                icon='undo',
                tip=_('Undo last edit made to the table.'),
                triggered=self._undo_edit,
                shortcut='Ctrl+Z',
                context=Qt.WidgetShortcut,
                name='undo_edits')
            self.undo_edits_action.setEnabled(False)
            self._actions['edit'].append(self.undo_edits_action)
        if 'redo_edits' not in self._disabled_actions:
            self.redo_edits_action = create_action(
                self, _("Redo"),
                icon='redo',
                tip=_('Redo the last edit that was undone.'),
                triggered=self._redo_edit,
                shortcut='Ctrl+Shift+Z',
                context=Qt.WidgetShortcut,
                name='redo_edits')
            self.redo_edits_action.setEnabled(False)
            self._actions['edit'].append(self.redo_edits_action)
        self.addActions(self._actions['edit'])

        # ---- Setup selection actions.
        if 'selection' not in self._disabled_actions:
            select_all_action = create_action(
                self, _("Select All"),
                icon='select_all',
                tip=_("Select all items in the table."),
                triggered=self.select_all,
                shortcut='Ctrl+A',
                context=Qt.WidgetShortcut,
                name='select_all')
            select_clear_action = create_action(
                self, _("Clear Selection"),
                icon='select_clear',
                tip=_("Clear the selection in the table."),
                triggered=lambda _: self.selectionModel().clearSelection(),
                shortcut='Escape',
                context=Qt.WidgetShortcut,
                name='clear_selection')
            select_row_action = create_action(
                self, _("Select Row"),
                icon='select_row',
                tip=_("Select the entire row of the current selection. "
                      "If the current selection spans multiple rows, "
                      "all rows that intersect the selection will be "
                      "selected."),
                triggered=self.select_row,
                shortcut='Shift+Space',
                context=Qt.WidgetShortcut,
                name='select_row')
            select_column_action = create_action(
                self, _("Select Column"),
                icon='select_column',
                tip=_("Select the entire column of the current selection. "
                      "If the current selection spans multiple columns, all "
                      "columns that intersect the selection will "
                      "be selected."),
                triggered=self.select_column,
                shortcut='Ctrl+Space',
                context=Qt.WidgetShortcut,
                name='select_column')
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
                    self.sort_by_current_column(Qt.AscendingOrder),
                name='sort_ascending')
            sort_descending_action = create_action(
                self, _("Sort Descending"),
                icon='sort_descending',
                tip=_("Reorder rows by sorting the data of the current column "
                      "in descending order."),
                shortcut="Ctrl+>",
                context=Qt.WidgetShortcut,
                triggered=lambda _:
                    self.sort_by_current_column(Qt.DescendingOrder),
                name='sort_descending')
            sort_clear_action = create_action(
                self, _("Clear Sort"),
                icon='sort_clear',
                tip=_("Clear all sorts applied to the columns of the table."),
                triggered=lambda _: self.clear_sort(),
                shortcut="Ctrl+.",
                context=Qt.WidgetShortcut,
                name='sort_clear')
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
        if data_edit is None:
            # This means that all table model edits were cancelled.
            self._data_edit_cursor_pos.clear()
            self._update_actions_state()
            return

        if data_edit != self.model().last_edit():
            # This means that this given edit was just undone.
            self._update_actions_state()
            return

        if data_edit.id in self._data_edit_cursor_pos:
            # This means that this given edit was just redone.
            cursor_pos = self._data_edit_cursor_pos[data_edit.id]
            model_index = self.model().mapFromSource(
                self.source_model.index(*cursor_pos))

            self.selectionModel().clearSelection()
            self._ensure_visible(model_index)
            self.selectionModel().setCurrentIndex(
                model_index, self.selectionModel().NoUpdate)

            self._update_actions_state()
            return

        if data_edit.type() == SardesTableModelBase.AddRows:
            if self.visible_column_count():
                column = self.model().column_names().index(
                    self.visible_columns()[0])
            else:
                column = 0
            model_index = self.model().mapFromSource(
                self.source_model.index(data_edit.row[0], column))
            self._ensure_visible(model_index, force=True)
            self.setCurrentIndex(model_index)
        elif data_edit.type() == SardesTableModelBase.EditValue:
            model_index = self.model().mapFromSource(
                self.source_model.index(data_edit.row, data_edit.col))
            self._ensure_visible(model_index)
            self.setCurrentIndex(model_index)
        elif data_edit.type() == SardesTableModelBase.DeleteRows:
            pass

        # Save the cursor position for that edit.
        current_source_index = self.model().mapToSource(
            self.current_index())
        self._data_edit_cursor_pos[data_edit.id] = (
            current_source_index.row(), current_source_index.column())

        self._update_actions_state()

    def _update_actions_state(self):
        """
        Update the states of this tableview actions.
        """
        current_index = self.current_index()
        if current_index.isValid():
            is_editable = self.is_data_editable_at(current_index)
            is_clearable = self.is_data_clearable_at(current_index)
            if 'clear_item' not in self._disabled_actions:
                self.clear_item_action.setEnabled(is_clearable)
            if 'edit_item' not in self._disabled_actions:
                self.edit_item_action.setEnabled(is_editable)

        has_unsaved_data_edits = self.model().has_unsaved_data_edits()
        if 'save_edits' not in self._disabled_actions:
            self.save_edits_action.setEnabled(has_unsaved_data_edits)
        if 'undo_edits' not in self._disabled_actions:
            self.undo_edits_action.setEnabled(
                bool(self.model().data_edit_count()))
        if 'redo_edits' not in self._disabled_actions:
            self.redo_edits_action.setEnabled(
                bool(self.model().undone_edit_count()))
        if 'cancel_edits' not in self._disabled_actions:
            self.cancel_edits_action.setEnabled(has_unsaved_data_edits)

        self.sig_current_changed.emit(current_index)

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

    def confirm_before_saving_edits(self):
        """
        Return wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        return self.model().confirm_before_saving_edits()

    def set_confirm_before_saving_edits(self, x):
        """
        Set wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        self.model().set_confirm_before_saving_edits(x)

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
        self.sort_by_column(self.current_index().column(), sorting_order)

    # ---- Data selection
    def current_index(self):
        """
        Return the currently selected index in the table view.
        """
        return self.selectionModel().currentIndex()

    def current_data(self):
        """
        Return the value of the current index.
        """
        return self.current_index().data()

    def set_current_index(self, row, col, command='SelectCurrent'):
        """
        Set the current index in the table view to that corresponding to the
        provided logical row and column.
        """
        index = self.model().index(row, col)
        sm = self.selectionModel()
        sm.setCurrentIndex(index, getattr(sm, command))
        return index

    def select(self, row, col, command='Select'):
        """
        Do the selection operation at the specified row and col.
        """
        index = self.model().index(row, col)
        sm = self.selectionModel()
        sm.select(index, getattr(sm, command))
        return index

    def get_current_row_data(self):
        """
        Return the data relative to the row with the current item (the item
        with the focus).
        """
        model_index = self.current_index()
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
        current_column = self.current_index().column()
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
        current_index = self.current_index()
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
        current_index = self.current_index()
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
                self.model().column_names_headers_map(),
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

    def get_data_for_row(self, row):
        """
        Return the data currently displayed on the given row of this table.

        Note that the returned data is ordered according the columns visible
        indexes and that data for invisible columns is not included in the
        returned data.

        Parameters
        ----------
        row : int
            An integer corresponding to the index of the row for which
            data will be returned.

        Returns
        -------
        data : list of str
            A list of strings corresponding to the data currently displayed
            on the given row of this table.
        """
        data = []
        for i in range(self.column_count()):
            column = self.horizontalHeader().logicalIndex(i)
            if not self.horizontalHeader().isSectionHidden(column):
                data.append(self.model().index(row, column).data())
        return data

    def get_values_for_row(self, row):
        """
        Return the model values corresponding to the data currently displayed
        on the given row of this table.

        Note that the returned values are ordered according their respective
        column visible index and that values associated with invisible columns
        are not included in the returned list of values.

        Parameters
        ----------
        row : int
            An integer corresponding to the index of the row for which
            the model values will be returned.

        Returns
        -------
        data : list
            A list of model values corresponding to the data currently
            displayed on the given row of this table.
        """
        values = []
        for i in range(self.column_count()):
            column = self.horizontalHeader().logicalIndex(i)
            if not self.horizontalHeader().isSectionHidden(column):
                values.append(self.model().get_value_at(
                    self.model().index(row, column)))
        return values

    # ---- Column options
    def visible_columns(self):
        """
        Returns the list of data column names that are currently visible,
        ordered according to their visual index.
        """
        visible_columns = []
        for i in range(self.column_count()):
            logical_index = self.horizontalHeader().logicalIndex(i)
            if not self.horizontalHeader().isSectionHidden(logical_index):
                visible_columns.append(
                    self.model().column_names()[logical_index])
        return visible_columns

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
        for logical_index in range(self.source_model.columnCount()):
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
        return self.model().is_data_editable_at(model_index)

    def is_data_required_at(self, model_index):
        """
        Return whether a non null value is required for the item at the
        specified model index.
        """
        return self.model().is_data_required_at(model_index)

    def is_data_clearable_at(self, model_index):
        """
        Return whether the value of the cell at the specified model index
        is clearable or not.
        """
        return self.model().is_data_clearable_at(model_index)

    def _clear_current_item(self):
        """
        Set current item's data to None.
        """
        self.model().clear_model_data_at(self.current_index())

    def _edit_current_item(self):
        """
        Turn on edit mode for this table current cell.
        """
        current_index = self.current_index()
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
        self.closePersistentEditor(self.current_index())
        self.model().cancel_data_edits()

    def _undo_edit(self):
        """
        Undo the last edits that was made to the table.
        """
        self.closePersistentEditor(self.current_index())
        last_edit = self.model().last_edit()
        if last_edit.type() == SardesTableModelBase.AddRows:
            # We keep the selected item. If the selected item is part of the
            # addrow edit, which means that it will be removed by this undo
            # operation, we select the first item above it that is not
            # part of this edit.
            cur_index = self.current_index()
            sorted_rows = np.delete(
                np.arange(self.model().rowCount()),
                self.model()._map_row_from_source[last_edit.row])
            if len(sorted_rows) and cur_index.isValid():
                above_row_indexes = np.where(sorted_rows <= cur_index.row())[0]
                if len(above_row_indexes):
                    above_row = sorted_rows[above_row_indexes[-1]]
                else:
                    above_row = sorted_rows[0]
                source_model_index = self.model().mapToSource(
                    self.source_model.index(above_row, cur_index.column()))
            else:
                source_model_index = QModelIndex()

            self.model().undo_edit()
            model_index = self.model().mapFromSource(source_model_index)
        else:
            last_edit_cursor_pos = self._data_edit_cursor_pos[last_edit.id]
            self.model().undo_edit()
            model_index = self.model().mapFromSource(
                self.source_model.index(*last_edit_cursor_pos))

        self.selectionModel().clearSelection()
        self._ensure_visible(model_index)
        self.selectionModel().setCurrentIndex(
            model_index, self.selectionModel().NoUpdate)

    def _redo_edit(self):
        """
        Redo the last edit that was undone from the table.
        """
        self.closePersistentEditor(self.current_index())
        self.model().redo_edit()

    def _check_data_edits(self):
        """
        Check if the data edits can be safely saved in the database.
        """
        self.model().check_data_edits(self._handle_data_edits_checked)

    def _handle_data_edits_checked(self, error):
        """
        Handle results from the data edits check that is carried out
        before saving the edits to the database.
        """
        if error is None:
            self._save_data_edits(force=False)
        else:
            row, col = error.error_iloc(self)
            model_index = self.model().index(row, col)
            self._ensure_visible(model_index)
            self.selectionModel().setCurrentIndex(
                model_index, self.selectionModel().ClearAndSelect)

            msgbox = QMessageBox(
                QMessageBox.Warning,
                _('Error'),
                error.error_message(self),
                buttons=QMessageBox.Ok,
                parent=self)
            msgbox.button(msgbox.Ok).setText(_("OK"))
            msgbox.exec_()

    def _save_data_edits(self, force=True):
        """
        Save the data edits to the database. If 'force' is 'False', a message
        is first shown before proceeding.
        """
        if force is False and self.confirm_before_saving_edits():
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
            if chkbox.isChecked() is True:
                self.set_confirm_before_saving_edits(False)

        self.selectionModel().clearSelection()
        self.model().save_data_edits()

    def _add_new_row(self):
        """
        Add a new empty row at the end of this table.
        """
        self.model().add_new_row()

    def _append_row(self, values):
        """
        Append one or more new rows at the end of the data using the provided
        values.

        values: list of dict
            A list of dict containing the values of the rows that needs to be
            added to this SardesTableData. The keys of the dict must
            match the data..
        """
        self.model().append_row(values)

    def _delete_selected_rows(self):
        """Delete rows from the table with selected indexes"""
        rows = self.get_rows_intersecting_selection()
        self.model().delete_row(rows)
        if len(rows):
            self.sig_rows_deleted.emit(rows)

    def _ensure_visible(self, model_index, force=False):
        """
        Scroll to the item located at the given model index if it is not
        currently visible in the scrollarea.
        """
        # Make sure the column of the model index is visible.
        if self.horizontalHeader().isSectionHidden(model_index.column()):
            self.horizontalHeader().setSectionHidden(
                model_index.column(), False)

        item_rect = self.visualRect(model_index)
        view_rect = self.geometry()
        if not view_rect.contains(item_rect) or force:
            self.scrollTo(model_index, hint=self.PositionAtCenter)

    def show_message(self, title, message, func):
        """
        Show the provided message in a modal dialog.

        Parameters
        ----------
        title : str
            The message box title to be displayed.
        message : str
             The message box text to be displayed.
        func : {'about', 'critical', 'information', 'question', 'warning'}
            The type of message box to be displayed.
        """
        getattr(QMessageBox, func)(
            self, title, message, buttons=QMessageBox.Ok)

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
        # A dictionary containing the sardes tool installed in the table.
        self._tools = {}
        # A dictionary containing the actions registered to the table.
        self._actions = {}

        self.tableview = SardesTableView(
            table_model, self, multi_columns_sort, sections_movable,
            sections_hidable, disabled_actions)
        self.tableview.setAutoFillBackground(True)

        r255, b255, g255 = getattr(
            QStyleOption().palette, 'light')().color().getRgb()[:-1]
        viewport = self.tableview.viewport()
        viewport.setObjectName(str(id(viewport)))
        viewport.setStyleSheet(
            "#{} {{background-color: rgb({}, {}, {});}}"
            .format(str(id(viewport)), r255, b255, g255))

        self.tableview.sig_current_changed.connect(
            self.on_current_changed)

        self.progressbar = ProcessStatusBar(self, 96, 16, Qt.Vertical)
        self._end_process_timer = QTimer(self)
        self._end_process_timer.setSingleShot(True)
        self._end_process_timer.timeout.connect(self._end_process)
        self._end_process_timer._status_message = None

        self.model().sig_data_about_to_be_updated.connect(
            lambda: self._start_process(None))
        self.model().sig_data_updated.connect(self._handle_data_updated)
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

    # ---- Tableview Public API
    def __getattr__(self, name):
        """
        Expose the attributes of the tableview because the tablewidget is
        conceptually simply an extension of a tableview and should have
        the same interface.
        """
        try:
            return super().__getattr__(name)
        except AttributeError as error:
            try:
                return getattr(self.tableview, name)
            except AttributeError:
                raise error

    # ---- Layout
    def install_message_box(self, message_box):
        """
        Add the given message box to this table widget.
        """
        self.message_layout.addWidget(message_box)
        message_box.hide()
        return message_box

    # ---- Public methods
    def on_current_changed(self, current_index: QModelIndex):
        """
        Called when the current index in the table view changed.

        All sardes table widget that inherit this class should reimplement
        this method to change the state of its UI when the current index
        of the table view changes.
        """
        for tool in self.tools():
            tool.on_current_changed(current_index)

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

    def table_title(self):
        """Return the title of the table of this table widget."""
        return self.tableview.source_model.title()

    def table_name(self):
        """Return the name of the table of the table widget."""
        return self.tableview.source_model.name()

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
            for action in actions:
                toolbar.addAction(action)
                self._actions[action.objectName()] = action
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
    def add_toolbar_widget(self, widget, which='upper', before=None,
                           after=None):
        """
        Add a new widget to the uppermost toolbar if 'which' is 'upper',
        else add it to the lowermost toolbar.
        """
        if which == 'upper':
            toolbar = self.get_upper_toolbar()
            if before is not None:
                before = self._actions[before]
                action = toolbar.insertWidget(before, widget)
            elif after is not None:
                try:
                    index = toolbar.actions().index(self._actions[after])
                    before = toolbar.actions()[index + 1]
                except IndexError:
                    action = toolbar.addWidget(widget)
                else:
                    action = toolbar.insertWidget(before, widget)
            else:
                if self._upper_toolbar_separator is None:
                    action = toolbar.addWidget(widget)
                else:
                    action = toolbar.insertWidget(
                        self._upper_toolbar_separator, widget)
        else:
            action = self.get_lower_toolbar().addWidget(widget)
        return action

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

    # ---- Tools
    def tools(self):
        """
        Return the list of SardesTool currently installed in this table.
        """
        return self._tools.values()

    def install_tool(self, tool, before=None, after=None):
        """
        Install the provided tool in the toolbar of this tablewidget.

        The tool is inserted in the toolbar of this tablewidget before or
        after the provided after or before action or tool. If no before or
        after action or tool is specified, the tool is added at the end of
        the toolbar.

        Parameters
        ----------
        tool : SardesTool
            A sardes tool object to install to the toolbar of this tablewidget.
        before : str, optional
            The name of the action or tool before which the provided tool
            will be inserted in the toolbar of this tablewidget.
        after : str, optional
            The name of the action or tool after which the provided tool
            will be inserted in the toolbar of this tablewidget.
        """
        if tool.objectName() in self._tools:
            raise Warning(
                "Cannot add tool '{}' to table '{}' because there is already "
                "a tool installed with this name."
                ).format(tool.name, self.model().table_id)
            return
        if tool.objectName() in self._actions:
            raise Warning(
                "Cannot add tool '{}' to table '{}' because there is already "
                "an action with this name."
                ).format(tool.name, self.model().table_id)
            return

        self._actions[tool.objectName()] = self.add_toolbar_widget(
            tool.toolbutton(), 'upper', before, after)
        self._tools[tool.objectName()] = tool

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

    def _handle_data_updated(self):
        """
        Handle when the data of the model of this table widget have
        been updated.
        """
        for tool in self.tools():
            tool.update()
        self._handle_process_ended()

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
            tab_text = table.table_title()
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
