from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from collections import OrderedDict
import json
from utilities import *

class QParamEdit(QTableWidget):

    def __init__(self, parent=None):
        super(QParamEdit, self).__init__(parent)

        self.setStyleSheet("QParamEdit {border:0px;background-color:transparent;} QParamEdit::item {margin-bottom:3px;margin-right:5px;}")
        self.setShowGrid(False)
        self.nameoptions = []
        self.valueoptions = {}

        #Cols
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Name','Value'])
        self.horizontalHeader().setVisible(False)
        self.setColumnWidth(0,200)
        self.setColumnWidth(1,150)
        self.horizontalHeader().setStretchLastSection(True)

        #Rows
        self.setRowCount(0)
        self.verticalHeader().setVisible(False)
        self.isCalculating = False
        self.cellChanged.connect(self.calcRows)
        self.calcRows()
        self.resizeRowsToContents()

        self.horizontalScrollBar().setVisible(False)
        
    # Takes params as dict and fills the widget
    def setParams(self,vals={}):
        try:
            if isinstance(vals,str):
                vals = json.loads(vals)
        except:
            vals = {}

        self.setRowCount(len(vals))
        self.setValueOptionsAll(self.valueoptions)
        self.setNameOptionsAll(self.nameoptions)

        row = 0
        vals = dictToTuples(vals)
        for name, value in vals:
            # Set name
            self.setValue(row,0, name)

            # Set options
            combobox = self.getNameComboBox(row)
            options = combobox.itemData(combobox.currentIndex(), Qt.UserRole)
            self.setValueOptions(row, options)

            # Set value
            self.setValue(row,1, value)
            row = row+1

        self.calcRows()
        self.resizeRowsToContents()

    # Returns the params set in the widget
    def getParams(self):
        params = OrderedDict()
        for row in range(0,self.rowCount()):
            if not self.rowEmpty(row):
                key = self.getValue(row,0).strip()
                value = self.getValue(row,1).strip()

                if not key in params:
                    params[key] = value
                elif isinstance(params[key],list):
                    params[key].append(value)
                else:
                    params[key] = [params[key],value]

                #params[self.getValue(row,0).strip()] =
        return params


    def setNameOptionsAll(self, options):
        '''
        Sets the items in the left comboboxes
        options should be a list of dicts
        dicts can contain the following keys: name, doc, required, default, options
        '''

        self.isCalculating = True
        self.nameoptions = options

        for row in range(0, self.rowCount()):
            self.setNameOptions(row, options)
        self.isCalculating = False

    def setNameOptions(self, row, options):
        combo = self.getNameComboBox(row)
        combo.clear()

        # Insert items and set tooltips
        for o in reversed(options):
            # Add name
            name = o.get("name", "")
            name = "<" + name + ">" if o.get("in", "query") == "path" else name
            combo.insertItem(0, name)
            combo.setItemData(0,wraptip(o.get("description", None)), Qt.ToolTipRole)

            # set color
            if (o.get("required", False)):
                combo.setItemData(0, QColor("#FF333D"), Qt.BackgroundColorRole)

            # save options as suggestion for value box
            combo.setItemData(0, o, Qt.UserRole)

        # Insert empty item
        combo.insertItem(0, "")

        return (combo)

    def setValueOptionsAll(self, options):
        self.isCalculating = True
        self.valueoptions=options

        for row in range(0, self.rowCount()):
            self.setValueOptions(row, options)
        self.isCalculating = False

    def setValueOptions(self, row, options):
        combo = self.getValueComboBox(row)
        combo.clear()

        if not options:
            options = self.valueoptions

        schema = options.get("schema", {})

        # Get options
        if schema.get('type') == 'array':
            items = schema.get('items', {})
            enum = items.get('enum', [])
            oneof = items.get('oneOf', [])
        else:
            enum = schema.get('enum', [])
            oneof = schema.get('oneOf', [])

        for value in reversed(enum):
            combo.insertItem(0, value)

        for value in reversed(oneof):
            combo.insertItem(0, value.get('const', ''))
            combo.setItemData(0, wraptip(value.get("description", None)), Qt.ToolTipRole)

        # Default options
        if not len(enum) and not len(oneof) and schema.get('type') == 'boolean':
            combo.insertItem(0, '0')
            combo.insertItem(0, '1')
        if not len(enum) and not len(oneof) and schema.get('type') == 'boolean':
            combo.insertItem(0, '0')
            combo.insertItem(0, '1')
        else:
            combo.insertItem(0, '<Object ID>')
            combo.setItemData(0, wraptip('The value in the Object ID-column in the data view.'), Qt.ToolTipRole)
            combo.insertItem(0, '')

        # Select default value
        if options.get('required', False) and not ('example' in options):
            value = '<Object ID>'
        else:
            value = options.get('example', '')

        self.setValue(row, 1, value)

        return (combo)

    def getNameComboBox(self, row):
        combo = self.cellWidget(row,0)
        if combo is None:
            combo=QComboBox(self)
            combo.setEditable(True)
            combo.setMinimumContentsLength(25)
            combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
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
            combo.setMinimumContentsLength(20)
            combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)

            combo.row = row
            combo.col = 1
            combo.editTextChanged.connect(self.calcRows)
            combo.activated.connect(self.onItemSelected)

            self.setCellWidget(row,1,value)
        else:
            combo = value.comboBox

        return (combo)



    def setValue(self,row,col,val):
        if col == 0:
            combo = self.getNameComboBox(row)
        else:
            combo = self.getValueComboBox(row)

        try:
            if isinstance(val,dict) or isinstance(val,list):
                val = json.dumps(val)
        except:
            val = ''

        index = combo.findText(val)
        if index != -1:
            combo.setCurrentIndex(index)
        else:
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


    def initRow(self, row):
        self.setNameOptions(row, self.nameoptions)
        self.setValue(row, 0, '')
        self.setValueOptions(row, self.valueoptions)
        self.setValue(row, 1, '')


    def calcRows(self):
        #self.cellChanged.disconnect(self.calcRows)
        #self.cellChanged.connect(self.calcRows)
        #myTable.blockSignals(True)
        #myTable.blockSignals(False)

        if (self.isCalculating):
            return (False)
        self.isCalculating = True

        #Remove empty
        for row in range(self.rowCount()-1,-1,-1):
            if self.rowEmpty(row):
                self.removeRow(row)

        #Add last row
        row = self.rowCount()
        self.setRowCount(row+1)

        self.initRow(row)

        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.verticalResizeTableViewToContents()
        self.isCalculating = False

    @Slot()
    def onItemSelected(self,index=0):
        '''
        Value suggestions for right side
        '''
        sender = self.sender()
        if hasattr(sender,'col') and hasattr(sender,'row') and (sender.col == 0):
            # Get options
            options = sender.itemData(index, Qt.UserRole)
            # Set options
            self.setValueOptions(sender.row, options)



    def verticalResizeTableViewToContents(self):

        rowTotalHeight=0
        count= self.verticalHeader().count()
        for i in range(count):
            if (not self.verticalHeader().isSectionHidden(i)):
                rowTotalHeight += self.verticalHeader().sectionSize(i)

        #Check for scrollbar visibility
        if (not self.horizontalScrollBar().isHidden()):
             rowTotalHeight += self.horizontalScrollBar().height()

        # Check for header visibility
        if (not self.horizontalHeader().isHidden()):
             rowTotalHeight += self.horizontalHeader().height()

        self.setMinimumHeight(rowTotalHeight)
        self.setMaximumHeight(rowTotalHeight)

class ValueEdit(QWidget):
    def __init__(self,parent):
        super(ValueEdit, self).__init__(parent)

        self.mainLayout = QHBoxLayout(self)
        self.mainLayout.setContentsMargins(5,0,0,0)
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
        input.setMinimumWidth(50)
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

