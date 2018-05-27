from PySide.QtCore import *
from PySide.QtGui import *

class QParamEdit(QTableWidget):

    def __init__(self, parent=None):
        super(QParamEdit, self).__init__(parent)

        self.setStyleSheet("QParamEdit {border:0px;} QParamEdit::item {margin-bottom:3px;margin-right:5px;}")
        self.setShowGrid(False)
        self.nameoptions = []
        self.valueoptions = []

        #Cols
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Name','Value'])
        self.horizontalHeader().setVisible(False)
        self.setColumnWidth(0,150)
        self.setColumnWidth(1,150)
        self.horizontalHeader().setStretchLastSection(True)

        #Rows
        self.setRowCount(0)
        self.verticalHeader().setVisible(False)
        self.isCalculating = False
        self.cellChanged.connect(self.calcRows)
        self.calcRows()
        self.resizeRowsToContents()

    # Takes params as dict and fills the widget
    def setParams(self,vals={}):
        self.setRowCount(len(vals))
        self.setValueOptions(self.valueoptions)
        self.setNameOptions(self.nameoptions)

        row = 0
        for name in vals:
            self.setValue(row,0, name)
            self.setValue(row,1, vals[name])
            row = row+1

        self.calcRows()
        self.resizeRowsToContents()

    # Returns the params set in the widget
    def getParams(self):
        params = {}
        for row in range(0,self.rowCount()):
            if not self.rowEmpty(row):
                params[self.getValue(row,0).strip()] = self.getValue(row,1).strip()
        return params

    def initParamName(self, row):
        self.setNameComboBox(row, self.nameoptions)
        self.setValue(row, 0, '')

    def initParamValue(self, row):
        self.setValueComboBox(row, self.valueoptions)
        self.setValue(row, 1, '')

    def setNameOptions(self, options):
        '''
        Sets the items in the left comboboxes
        options should be a list of dicts
        dicts can contain the following keys: name, doc, required, default, options
        '''

        self.isCalculating = True
        self.nameoptions = options

        for row in range(0, self.rowCount()):
            self.setNameComboBox(row,options)
        self.isCalculating = False

    def setValueOptions(self, options):
        self.isCalculating = True
        self.valueoptions=options

        for row in range(0, self.rowCount()):
            self.setValueComboBox(row,options)
        self.isCalculating = False

    def getNameComboBox(self, row):
        combo = self.cellWidget(row,0)
        if combo is None:
            combo=QComboBox(self)
            combo.setEditable(True)
            combo.row = row
            combo.col = 0
            combo.editTextChanged.connect(self.calcRows)
            combo.activated.connect(self.onItemSelected)
            self.setCellWidget(row,0,combo)

        return (combo)

    def getValueComboBox(self, row):

        value = self.cellWidget(row,1)

        if value is None:
            value = ValueEdit(self)
            combo = value.comboBox

            combo.row = row
            combo.col = 1
            combo.editTextChanged.connect(self.calcRows)
            combo.activated.connect(self.onItemSelected)

            self.setCellWidget(row,1,value)
        else:
            combo = value.comboBox

        return (combo)

    def setNameComboBox(self,row,options):
        combo = self.getNameComboBox(row)
        combo.clear()
        # edited: Insert each Item seperatly and set Tooltip
        for o in reversed(options):
            combo.insertItem(0,o.get("name",""))
            # this one sets the tooltip
            combo.setItemData(0,o.get("doc",None),Qt.ToolTipRole)
            #set color
            if (o.get("required",False)):
                combo.setItemData(0,QColor("#FF333D"),Qt.BackgroundColorRole)
            #save options as suggestion for value box
            if ('options' in o):
                combo.setItemData(0,o.get("options",[]),Qt.UserRole)

        return (combo)

    def setValueComboBox(self,row,options):
        combo = self.getValueComboBox(row)
        combo.clear()
        # edited: Insert each Item seperatly and set Tooltip
        for o in reversed(options):
            combo.insertItem(0,o.get("name",""))
            # this one sets the tooltip
            combo.setItemData(0,o.get("doc",None),Qt.ToolTipRole)
            #set color
            if (o.get("required",False)):
                combo.setItemData(0,QColor("#FF333D"),Qt.BackgroundColorRole)
            #save options as suggestion for value box
            if ('options' in o):
                combo.setItemData(0,o.get("options",[]),Qt.UserRole)

        return (combo)

    def setValue(self,row,col,val):
        if col == 0:
            combo = self.getNameComboBox(row)
        else:
            combo = self.getValueComboBox(row)

        combo.setEditText(val)

    def getValue(self,row,col):
        if col == 0:
            combo = self.getNameComboBox(row)
        else:
            combo = self.getValueComboBox(row)

        return(combo.currentText())



    def rowEmpty(self,row):
        col0 = self.getValue(row,0).strip()
        col1 = self.getValue(row,1).strip()

        return (((col0 == '<None>') | (col0 == '')) & ((col1 == '<None>') | (col1 == '')))

    @Slot()
    def onItemSelected(self,index=0):
        '''
        If sender is in first column sets value suggestions
        '''
        sender = self.sender()
        options = sender.itemData(index,Qt.UserRole)
        if not options:
            options = self.valueoptions
        if hasattr(sender,'col') and hasattr(sender,'row') and (sender.col == 0):
            self.setValueComboBox(sender.row, options)



    def calcRows(self):
        #self.cellChanged.disconnect(self.calcRows)
        #self.cellChanged.connect(self.calcRows)
        #myTable.blockSignals(True)
        #myTable.blockSignals(False)

        if (self.isCalculating): return (False)
        self.isCalculating = True

        #Remove empty
        for row in range(self.rowCount()-1,-1,-1):
            if self.rowEmpty(row):
                self.removeRow(row)

        #Add last row
        row = self.rowCount()
        self.setRowCount(row+1)

        self.initParamName(row)
        self.initParamValue(row)

        self.resizeRowsToContents()
        self.isCalculating = False


class ValueEdit(QWidget):
    def __init__(self,parent):
        super(ValueEdit, self).__init__(parent)

        self.mainLayout = QHBoxLayout(self)
        self.mainLayout.setContentsMargins(0,0,0,0)
        self.setLayout(self.mainLayout)

        self.comboBox = QComboBox(self)
        self.comboBox.setEditable(True)


        self.actionEditValue = QAction('...',self)
        self.actionEditValue.setText('..')
        self.actionEditValue.triggered.connect(self.editValue)

        self.button =QToolButton(self)
        self.button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.button.setDefaultAction(self.actionEditValue)

        self.mainLayout.addWidget(self.comboBox,2)
        self.mainLayout.addWidget(self.button,0)

    def editValue(self):
        dialog = QDialog(self,Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        dialog.setWindowTitle("Edit value")
        layout = QVBoxLayout()


        input = QPlainTextEdit()
        input.setMinimumWidth(400)
        input.setPlainText(self.comboBox.currentText())
        #input.LineWrapMode = QPlainTextEdit.NoWrap
        #input.acceptRichText=False
        input.setFocus()
        layout.addWidget(input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        dialog.setLayout(layout)

        def setValue():
            value = input.toPlainText() #input.toPlainText().splitlines()
            self.comboBox.setEditText(value)

            dialog.close()

        def close():
            dialog.close()

        #connect the nested functions above to the dialog-buttons
        buttons.accepted.connect(setValue)
        buttons.rejected.connect(close)
        dialog.exec_()

