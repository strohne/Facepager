from PySide.QtCore import *
from PySide.QtGui import *


class ProgressBar(QProgressDialog):

    valueChanged = Signal(int)

    def __init__(self, mainmessage, buttontext,parent=None, min=0, max=0, interval=5,intervalmessage=None):
        super(ProgressBar,self).__init__(mainmessage,buttontext,min,max,parent)
        # set initial up values        
        self.delayedmaximum = max
        self.setMinimumDuration(0)
        self.setLabelText(mainmessage)
        self.setCancelButtonText(buttontext)
        self.setWindowModality(Qt.WindowModal)
        self.forceShow()
        self.setAutoReset(False)
        self.setAutoClose(False)
        
        #set date
        self.interval = interval
        self.interval_nextupdate = None
        self.interval_message = intervalmessage
        
        #self.valueChanged.connect(self.printChange)
        self.setValue(0)
        

    def setValue(self, progress):
        '''
        override setValue to calculate speed 
        emits valueChanged signal which is not available in the progress dialog
        '''
        super(ProgressBar,self).setValue(progress)           
        self.computeRate()                 
        self.valueChanged.emit(progress)

    def setMaximum(self,maximum,delay=True):
        '''
        override setMaximum to keep endless progress bar until first step was done
        '''
        self.delayedmaximum = maximum
        if not delay:
            super(ProgressBar,self).setMaximum(maximum)
        
    def step(self):
        '''
        Increment progress bar for one step
        '''
        
        self.setMaximum(self.delayedmaximum, False)        
        self.setValue(self.value() + 1)
        
        
    @Slot()
    def printChange(self,int):
        print int

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



               
