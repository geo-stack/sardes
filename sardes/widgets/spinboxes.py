# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
from qtpy.QtCore import QSize, Signal
from qtpy.QtWidgets import QWidget, QHBoxLayout, QDoubleSpinBox, QLabel

# ---- Local imports
from sardes.config.icons import get_icon
from sardes.utils.qthelpers import format_tooltip


class IconSpinBox(QWidget):
    """
    A spinbox with an icon to its left.
    """
    sig_value_changed = Signal(float)

    def __init__(self, icon, value=0, value_range=(0, 99), decimals=0,
                 single_step=1, suffix=None, text=None, tip=None, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 5, 0)
        layout.setSpacing(1)

        self.spinbox = QDoubleSpinBox()
        self.spinbox.setDecimals(decimals)
        self.spinbox.setRange(*value_range)
        self.spinbox.setSingleStep(single_step)
        self.spinbox.setValue(value)
        self.spinbox.valueChanged.connect(self.sig_value_changed.emit)
        if suffix is not None:
            self.spinbox.setSuffix(suffix)

        icon_label = QLabel()
        icon_label.setPixmap(get_icon(icon).pixmap(
            QSize(self.spinbox.sizeHint().height(),
                  self.spinbox.sizeHint().height())))

        layout.addWidget(icon_label)
        layout.addWidget(self.spinbox)

        if any((text, tip)):
            self.spinbox.setToolTip(format_tooltip(text, tip, None))
            icon_label.setToolTip(format_tooltip(text, tip, None))

    # ---- QHBoxLayout public API
    def setContentsMargins(self, *margins):
        return self.layout().setContentsMargins(*margins)

    # ---- QDoubleSpinBox public API
    def setValue(self, val):
        return self.spinbox.setValue(val)

    def value(self):
        return self.spinbox.value()
