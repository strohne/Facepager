from PySide.QtCore import *
from PySide.QtGui import *
from models import *
import time
import os
import icons


class Toolbar(QToolBar):
    '''
    Initialize the main toolbar for the facepager-too that provides the central interface and functions.
    '''
    def __init__(self,parent=None,mainWindow=None):
        super(Toolbar,self).__init__(parent)
        self.mainWindow=mainWindow
        self.setIconSize(QSize(32,32))
        
        self.addActions(self.mainWindow.actions.basicActions.actions())        
        self.addSeparator()
        self.addActions(self.mainWindow.actions.databaseActions.actions())

        

            
    

            
    

