
class HGSurveyImportDialog(QDialog):
    """
    A dialog window to import hg surveys from an Excel Workbook.
    """
    sig_closed = Signal()
    sig_import_request = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('Import HG Surveys'))
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowIcon(get_icon('master'))
        self.setModal(False)
        self.setWindowModality(Qt.ApplicationModal)
        self.__setup__()

    def __setup__(self):
        """Setup the dialog with the provided settings."""
        self.input_file_pathbox = PathBoxWidget(
            path_type='getOpenFileName',
            filters="Excel Workbook (*.xlsx)")
        self.input_file_pathbox.browse_btn.setText(_('Select...'))
        self.input_file_pathbox.browse_btn.setToolTip(format_tooltip(
            text=_("Select Import File"),
            tip=_("Select an xlsx files containing the hg survey data "
                  "to import in the database."),
            shortcuts=None
            ))
        self.input_file_pathbox.path_lineedit.setMinimumWidth(300)
        self.input_file_pathbox.sig_path_changed.connect(
            self._handle_xlsxfile_selected)

        # Setup the status bar.
        self.status_bar = ProcessStatusBar()
        self.status_bar.hide()

        # Setup the dialog button box.
        self.import_btn = QPushButton(_('Import'))
        self.import_btn.setDefault(True)
        self.import_btn.clicked.connect(
            lambda: self.sig_import_request.emit(True))
        self.import_btn.setEnabled(False)

        self.close_btn = QPushButton(_('Close'))
        self.close_btn.setDefault(False)
        self.close_btn.setAutoDefault(False)
        self.close_btn.clicked.connect(self.close)

        self.cancel_btn = QPushButton(_('Cancel'))
        self.cancel_btn.setDefault(False)
        self.cancel_btn.setAutoDefault(False)
        self.cancel_btn.clicked.connect(
            lambda: self._handle_cancel_import())
        self.cancel_btn.setVisible(False)

        self.continue_btn = QPushButton(_('Continue'))
        self.continue_btn.setDefault(False)
        self.continue_btn.setAutoDefault(False)
        self.continue_btn.clicked.connect(
            lambda: self._handle_continue_import())
        self.continue_btn.setVisible(False)

        button_box = QDialogButtonBox()
        button_box.layout().addStretch(1)
        button_box.layout().addWidget(self.import_btn)
        button_box.layout().addWidget(self.close_btn)
        button_box.layout().addWidget(self.cancel_btn)
        button_box.layout().addWidget(self.continue_btn)
        button_box.layout().setContentsMargins(*get_default_contents_margins())

        # Setup the base widget.
        base_widget = QWidget()

        base_layout = QVBoxLayout(base_widget)
        base_layout.addWidget(QLabel(
            _("Select a valid hg survey input file :")
            ))
        base_layout.addWidget(self.input_file_pathbox)
        base_layout.addWidget(self.status_bar)
        base_layout.setStretch(0, 1)

        # Setup the unsaved changes warning message.
        self.unsaved_changes_dialog = ProcessStatusBar(
            spacing=10,
            icon_valign='top',
            iconsize=get_standard_iconsize('messagebox'),
            contents_margin=get_default_contents_margins())
        self.unsaved_changes_dialog.set_icon(
            'failed', get_standard_icon('SP_MessageBoxWarning'))

        self.unsaved_changes_dialog.setAutoFillBackground(True)
        palette = QApplication.instance().palette()
        palette.setColor(
            self.unsaved_changes_dialog.backgroundRole(),
            palette.light().color())
        self.unsaved_changes_dialog.setPalette(palette)

        # Setup the stacked widget.
        self.stackwidget = QStackedWidget()
        self.stackwidget.addWidget(base_widget)
        self.stackwidget.addWidget(self.unsaved_changes_dialog)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.stackwidget)
        main_layout.addWidget(button_box)
        main_layout.setSizeConstraint(main_layout.SetFixedSize)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

    # ---- Public Interface
    def show_unsaved_changes_dialog(self, message: str):
        """
        Show a message to warn the user that there are unsaved changes in
        some tables that will be lost after importing hg survey data.
        """
        self.import_btn.setVisible(False)
        self.close_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.continue_btn.setVisible(True)
        self.unsaved_changes_dialog.show_fail_icon(message)
        self.stackwidget.setCurrentWidget(self.unsaved_changes_dialog)
        QApplication.beep()

    def close_unsaved_changes_dialog(self):
        """
        Close the unsaved changes dialog.
        """
        self.import_btn.setVisible(True)
        self.close_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.continue_btn.setVisible(False)
        self.stackwidget.setCurrentIndex(0)

    # ---- Handlers
    def _handle_continue_import(self):
        """
        Handle when the user has chosen to continue the import process
        in the "unsaved table changes" dialog.
        """
        self.close_unsaved_changes_dialog()
        self.sig_import_request.emit(False)

    def _handle_cancel_import(self):
        """
        Handle when the user has chosen to cancel the import process
        in the "unsaved table changes" dialog.
        """
        self.close_unsaved_changes_dialog()

    def _handle_xlsxfile_selected(self, path):
        """Handle when a new hg survey input xlsx file is selected."""
        self.import_btn.setEnabled(osp.exists(path) and osp.isfile(path))

if __name__ == '__main__':
    import sys
    from qtpy.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = HGSurveyImportDialog()
    dialog.show()
    sys.exit(app.exec_())
