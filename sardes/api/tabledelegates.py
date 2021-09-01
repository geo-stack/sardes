# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Standard imports
from datetime import datetime
from math import floor, ceil

# ---- Third party imports
import pandas as pd
from qtpy.QtCore import QEvent, Qt
from qtpy.QtGui import QPen, QPalette
from qtpy.QtWidgets import (
    QComboBox, QDateEdit, QDateTimeEdit, QDoubleSpinBox, QLineEdit,
    QSpinBox, QStyledItemDelegate, QTextEdit, QListView, QStyle)

# ---- Local imports
from sardes.config.locale import _
from sardes.utils.data_operations import are_values_equal
from sardes.utils.qthelpers import (
    qdatetime_from_datetime, get_datetime_from_editor)


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
        field_name = self.model().columns()[self.model_index.column()].header
        edited_value = self.get_editor_data()
        if (self.unique_constraint and self.model().is_value_in_column(
                self.model_index, edited_value)):
            return _(
                "<b>Duplicate key value violates unique constraint.</b>"
                "<br><br>"
                "The {} <i>{}</i> already exists. Please use another value."
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

    def format_data(self, data):
        """
        Format data according to the format prescribed by this delegate so that
        they can be safely added to the model's data.

        By default, this method does nothing and return the provided data and
        a null warning message. This method needs to be reimplemented for
        delegates that require specific data formatting.

        Parameters
        ----------
        data : Series
            A pandas Series that needs to be formatted to the format
            prescribed by this delegate so that its values can be safely
            added to the model's data.

        Returns
        -------
        formatted_data : Series
            The pandas Series formatted to the format prescribed by this
            delegates so that its values can be safely added to the
            model's data. Elements of the Series that could not be formatted
            according to the prescribed format are set to NaN.
        warning_message: str
            A text describing errors that could have occured while
            formatting the data.
        """
        return data, None


class NotEditableDelegate(SardesItemDelegate):
    """
    A delegate used to indicate that the items in the associated
    column are not editable.
    """

    def __init__(self, model_view):
        super().__init__(model_view, is_required=True)
        self.is_editable = False

    def createEditor(self, *args, **kargs):
        return None

    def setEditorData(self, *args, **kargs):
        pass

    def setModelData(self, *args, **kargs):
        pass

    def clear_model_data_at(self, *args, **kargs):
        pass

    # ---- SardesItemDelegate API
    def get_editor_data(self, *args, **kargs):
        pass

    def set_editor_data(self, *args, **kargs):
        pass

    def format_data(self, data):
        data.values[:] = None
        return data, None
