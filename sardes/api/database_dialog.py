# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Third party imports
from qtpy.QtWidgets import (QApplication, QGridLayout, QGroupBox, QLabel,
                            QVBoxLayout)


class DatabaseConnectDialogBase(QGroupBox):
    """
    Sardes database dialog class.

    This class provides a gui for the Sardes database accessor class.
    All database accessor classes that needs to be added to the Sardes
    database connection widget *must* inherit this class, extent the __init__
    constructor to add a gui, and reimplement the set_database_kargs and
    get_database_kargs methods.
    """
    # The concrete database accessor class this dialog is providing an
    # interface to. The accessor is not instantiated here because it is
    # going to be run in another thread than that of the gui.
    __DatabaseAccessor__ = None
    # The name given to the type of database this dialog is providing
    # an interface to.
    __database_type_name__ = None
    # A description of the database this dialog is providing an interface to.
    __database_type_desc__ = ''

    def __init__(self):
        super().__init__()

        # Setup this dialog style.
        self.setAutoFillBackground(True)
        palette = QApplication.instance().palette()
        palette.setColor(self.backgroundRole(), palette.light().color())
        self.setPalette(palette)

        # Setup this dialog layout.
        self.layout = QVBoxLayout(self)

        if self.dbtype_desc:
            dbtype_desc_label = QLabel(self.dbtype_desc)
            dbtype_desc_label.setWordWrap(True)
            self.layout.addWidget(dbtype_desc_label)

        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)

    @property
    def dbtype_name(self):
        """
        Return the name given to the type of database this dialog is providing
        an interface to.
        """
        if self.__database_type_name__ is None:
            raise NotImplementedError
        else:
            return self.__database_type_name__

    @property
    def dbtype_desc(self):
        """
        Return a description of the database this dialog is providing an
        interface to.
        """
        return self.__database_type_desc__

    def create_database_accessor(self):
        """
        Return an instance of the database accessor class this dialog
        is providing an interface to.
        """
        return self.__DatabaseAccessor__(**self.get_database_kargs())

    def add_widget(self, *args, **kargs):
        """
        Add the given widget to this dialog's layout at row and column
        with the specified row and column spans. The widget will have the
        given alignment.
        """
        self.form_layout.addWidget(*args, **kargs)

    def add_layout(self, *args, **kargs):
        """
        Add the given layout to this dialog's layout at row and column
        with the specified row and column spans. The layout will have the
        given alignment.
        """
        self.form_layout.addLayout(*args, **kargs)

    def add_stretch(self, stretch):
        """
        Adds a stretchable space with zero minimum size and stretch factor
        stretch to the end of this dialog layout.
        """
        self.form_layout.setRowStretch(self.form_layout.rowCount(), stretch)

    def set_database_kargs(self, kargs):
        """
        Setup the dialog form widgets with the provided values in the
        kargs dict.
        """
        pass

    def get_database_kargs(self):
        """
        Return a dict that must match the constructor kargs signature of the
        database accessor class for which this dialog is providing an
        an interface to.
        """
        return {}
