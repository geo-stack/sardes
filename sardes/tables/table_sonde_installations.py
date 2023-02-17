# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMessageBox, QCheckBox

# ---- Local imports
from sardes.api.tablemodels import (
    SardesTableColumn, sardes_table_column_factory)
from sardes.config.locale import _
from sardes.widgets.tableviews import SardesTableWidget
from sardes.tables.models import StandardSardesTableModel
from sardes.tables.delegates import (
    ObsWellIdEditDelegate, SondesSelectionDelegate, TextEditDelegate,
    DateTimeDelegate, NumEditDelegate)


class SondeInstallationsTableModel(StandardSardesTableModel):
    """
    A table model to display the list of sondes currently installed or
    that were installed at some point in the observation wells for the
    entire monitoring network.
    """
    __tablename__ = 'table_sonde_installations'
    __tabletitle__ = _('Sonde Installations')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'sonde_installations', 'sampling_feature_uuid', _('Well ID'),
            delegate=ObsWellIdEditDelegate),
        sardes_table_column_factory(
            'sonde_installations', 'sonde_uuid', _('Serial - Brand Model'),
            delegate=SondesSelectionDelegate),
        sardes_table_column_factory(
            'sonde_installations', 'start_date', _('Date From'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"}),
        sardes_table_column_factory(
            'sonde_installations', 'end_date', _('Date To'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"}),
        sardes_table_column_factory(
            'sonde_installations', 'install_depth', _('Depth (m)'),
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': -99999, 'maximum': 99999}),
        sardes_table_column_factory(
            'sonde_installations', 'install_note', _('Notes'),
            delegate=TextEditDelegate)
        ]

    __dataname__ = 'sonde_installations'
    __libnames__ = ['observation_wells_data',
                    'sondes_data',
                    'sonde_models_lib']


class SondeInstallationsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = SondeInstallationsTableModel()
        super().__init__(table_model, *args, **kargs)
        self._show_delete_selected_rows_warning = True
        self.tableview.sig_rows_deleted.connect(self._on_rows_deleted)

    def _on_rows_deleted(self, rows):
        """
        Show a warning message after rows have been deleted from the table.
        """
        if self._show_delete_selected_rows_warning is False:
            return

        msgbox = QMessageBox(
            QMessageBox.Information,
            _('Warning'),
            _("<p>Note that readings data associated with a sonde "
              "installation that is being deleted are always kept in "
              "the database.</p>"
              "<p>However, the sonde and the depth of acquisition of these "
              "readings data will afterward be considered to be "
              "<b>unknow</b>.<br><br></p>"),
            buttons=QMessageBox.Ok,
            parent=self.tableview)
        msgbox.setTextInteractionFlags(Qt.TextSelectableByMouse)
        msgbox.button(msgbox.Ok).setText(_("OK"))

        chkbox = QCheckBox(
            _("Do not show this message again during this session."))
        msgbox.setCheckBox(chkbox)

        reply = msgbox.exec_()
        if reply == QMessageBox.Ok and chkbox.isChecked() is True:
            self._show_delete_selected_rows_warning = False
