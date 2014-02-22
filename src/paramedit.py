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
    
    def setNameOptions(self, options):
        self.isCalculating = True        
        self.nameoptions = options
      
        for row in range(0, self.rowCount()):
            self.setComboBox(row,0,options)
        self.isCalculating = False           
          
    def setValueOptions(self, options):
        self.isCalculating = True
        self.valueoptions=options

        for row in range(0, self.rowCount()):
            self.setComboBox(row,1,options)
        self.isCalculating = False      

    def getComboBox(self, row, col):
        combo = self.cellWidget(row,col)
        if combo is None:
            combo=QComboBox(self)
            combo.setEditable(True)    
            combo.editTextChanged.connect(self.calcRows)
            self.setCellWidget(row,col,combo)
        
        return (combo)
                    
    def setComboBox(self,row,col,options):
        combo = self.getComboBox(row,col)
        combo.clear()
        # edited: Insert each Item seperatly and set Tooltip
        for o in reversed(options):
            combo.insertItem(0,o[0])
            # this one sets the tooltip
            combo.setItemData(0,o[1],Qt.ToolTipRole)
            #set color
            if ((len(o) > 2) and (o[2])):
                combo.setItemData(0,QColor(Qt.darkRed),Qt.TextColorRole)

        return (combo)    
        
    def setValue(self,row,col,val):
        combo = self.getComboBox(row,col)
        combo.setEditText(val)
       
    def getValue(self,row,col):
        combo = self.getComboBox(row,col)
        return(combo.currentText())

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

    def getParams(self):
        params = {}
        for row in range(0,self.rowCount()):
            if not self.rowEmpty(row):
                params[self.getValue(row,0)] = self.getValue(row,1)
        return params  
            
    def rowEmpty(self,row):
        col0 = self.getValue(row,0)
        col1 = self.getValue(row,1)
        
        return (((col0 == '<None>') | (col0 == '')) & ((col1 == '<None>') | (col1 == '')))
                        
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
        self.setComboBox(row, 0, self.nameoptions)
        self.setComboBox(row, 1, self.valueoptions)
        self.setValue(row, 0, '')
        self.setValue(row, 1, '')

        self.resizeRowsToContents()
        self.isCalculating = False
        
        
        

