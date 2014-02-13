from PySide.QtCore import *
from PySide.QtGui import *


class ProgressBar(QProgressDialog):

    def __init__(self, mainmessage, buttontext,parent=None, min=0, max=0, interval=5,intervalmessage=None):
        super(ProgressBar,self).__init__("",buttontext,min,max,parent,Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        
        # set initial up values
        self.interval = interval
        self.interval_nextupdate = None
        self.interval_message = intervalmessage
        self.main_message = mainmessage
        
        self.setWindowTitle(mainmessage)
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumDuration(0)
        self.forceShow()
        self.setAutoReset(False)
        self.setAutoClose(False) #TODO: why doesn't this work anymore? Clicking cancel should not close window.
        self.setMaximum(max)
        self.setValue(0)

    def cancel(self):
        '''
        override cancel to automatically set maximum value when cancelling
        '''
        self.setValue(self.maximum())
        super(ProgressBar,self).cancel()  
        
        
    def setValue(self, progress):
        '''
        override setValue to calculate speed 
        emits valueChanged signal which is not available in the progress dialog
        '''
        super(ProgressBar,self).setValue(progress)           
        self.computeRate()                 

    def setMaximum(self,maximum,delay=True):
        '''
        override setMaximum to keep deleayed/endless progress bar until first step was done
        '''
        self.delayedmaximum = maximum
        if delay==False:
            super(ProgressBar,self).setMaximum(maximum)

    def step(self):
        '''
        Increment progress bar one step
        '''
        self.setMaximum(self.delayedmaximum, False)
        self.setValue(self.value() + 1)                

    def computeRate(self):
        '''
          compute the speed of operations
        '''
        if self.interval_nextupdate is None:
            self.interval_lastvalue = self.value()
            self.interval_lastupdate = QDateTime.currentDateTime()
            self.interval_nextupdate = self.interval_lastupdate.addSecs(self.interval)
            
        elif self.interval_message is not None and QDateTime.currentDateTime() > self.interval_nextupdate:            
            try:
                cur = QDateTime.currentDateTime()
                span = self.interval_lastupdate.secsTo(cur)
                rate = ((self.value() - self.interval_lastvalue) / float(span)) * 60
            except:
                rate = 0
            
            self.interval_lastupdate = cur
            self.interval_lastvalue = self.value()
            self.interval_nextupdate = self.interval_lastupdate.addSecs(self.interval)
                    
            self.setLabelText(self.interval_message.format(int(round(rate))))
            
    def showInfo(self,key,info):
        '''
          TODO: show additional information in the label 
        '''        
        pass
    