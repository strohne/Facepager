from PySide.QtCore import *
from PySide.QtGui import *


class ProgressBar(QProgressDialog):

    valueChanged = Signal(int)

    def __init__(self, mainmessage, buttontext, parent=None, min=0, max=100, interval=10):
        super(ProgressBar,self).__init__()
        # set initial up vales
        self.setRange(min, max)
        self.setMinimumDuration(0)
        self.setLabelText(mainmessage)
        self.setCancelButtonText(buttontext)
        self.setWindowModality(Qt.WindowModal)
        self.forceShow()
        self.setAutoReset(False)
        self.setAutoClose(False)
        #set date
        self.nowd = QDateTime.currentDateTime()
        self.nextd = self.nowd.addSecs(interval)
        self.valueChanged.connect(self.printChange)

    def setValue(self, int):
        '''
        override setValue and connect it with custom slot to mimic the QProgressBar.valueChanged-Signal
        which is not available in the progress dialog
        TODO: Connect this slot with the computeRate-method
        '''
        super(ProgressBar,self).setValue(int)
        self.valueChanged.emit(int)

    @Slot()
    def printChange(self,int):
        print int

    def computeRate(self):
        #compute the rate on every like in the queryNodes
        '''
                               if QDateTime.currentDateTime() > progress.nowd:
                            try:
                                cur = QDateTime.currentDateTime()
                                span = progress_lastupdate.secsTo(cur)
                                rate = ((progress_value - progress_lastvalue) / float(span)) * 60
                            except:
                                rate = 0

                            #progress_lastupdate = cur
                            #progress_lastvalue = progress_value
                            #progress_nextupdate = progress_lastupdate.addSecs(10);

                            #progress.setLabelText("Fetching data ({} nodes per minute)".format(int(round(rate))))

        '''








               
