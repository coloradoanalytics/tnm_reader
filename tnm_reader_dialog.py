import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'tnm_reader_dialog_base.ui'))

class TNMReaderDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(TNMReaderDialog, self).__init__(parent)
        self.setupUi(self)
        self.selectFileButton.clicked.connect(self.select_file)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def select_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select TNM .txf file", "", "*.txf")
        if filename:
            self.lineEdit.setText(filename)
