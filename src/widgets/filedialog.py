from PySide2.QtWidgets import QFileDialog, QComboBox, QLabel, QHBoxLayout


class CsvOpenDialog(QFileDialog):
    def __init__(self, parent=None, directory="", caption="Load CSV",  filter="CSV files (*.csv)"):
        super().__init__(parent, caption, directory, filter)

        # Set options for the QFileDialog
        self.setOption(QFileDialog.DontUseNativeDialog)
        self.setFileMode(QFileDialog.ExistingFile)
        self.setNameFilter(filter)

        # ComboBox for delimiter selection
        self.delimiters = {", (Comma)": ",", "; (Semicolon)": ";", "\\t (Tab)": "\t", "| (Pipe)": "|"}
        self.delimiter_label = QLabel("Delimiter:")
        self.delimiter_combo = QComboBox()
        self.delimiter_combo.addItems(self.delimiters.keys())

        # Find the layout of the dialog's widgets to insert custom controls
        # QFileDialog has a layout, insert a widget in its layout
        optionsLayout = QHBoxLayout()
        optionsLayout.addWidget(self.delimiter_label)
        optionsLayout.addWidget(self.delimiter_combo)
        optionsLayout.addStretch(1)

        mainLayout = self.layout()
        row = mainLayout.rowCount()
        mainLayout.addWidget(QLabel('Options'), row, 0)
        mainLayout.addLayout(optionsLayout, row, 1, 1, 2)

    def selectedDelimiter(self):
        text = self.delimiter_combo.currentText()
        return self.delimiters.get(text, ",")
