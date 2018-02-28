from PySide.QtCore import *
from PySide.QtGui import *
from datetime import timedelta

class ProgressBar(QDialog):

    def __init__(self, mainmessage, parent=None):
        #Init dialog
        super(ProgressBar,self).__init__(parent,Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(mainmessage)

        #Create layout
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.progressBar = QProgressBar()
        self.progressBar.setRange(0,0)
        layout.addWidget(self.progressBar,0)

        self.infoPanel = QFormLayout()
        self.infoPanel.setRowWrapPolicy(QFormLayout.DontWrapRows)
        self.infoPanel.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.infoPanel.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.infoPanel.setLabelAlignment(Qt.AlignLeft)
        self.infos = {}
        layout.addLayout(self.infoPanel)

        buttons = QDialogButtonBox()
        self.cancelButton = QPushButton(u"Cancel")
        self.cancelButton.clicked.connect(self.cancel)
        buttons.addButton(self.cancelButton,QDialogButtonBox.ActionRole)
        layout.addWidget(buttons)

        # set initial values
        self.wasCanceled = False

        #show
        self.open()


    def cancel(self):
        '''
        Set cancel flag, but doesn't close the dialog
        '''
        self.wasCanceled = True
        self.cancelButton.setText("Please wait...")
        self.cancelButton.setDisabled(True)


    def close(self):
        return super(ProgressBar,self).close()

    def setValue(self, progress):
        '''
        set value of the progressbar
        '''
        self.progressBar.setValue(progress)
        self.computeRate()

    def setMaximum(self,maximum,delay=True):
        '''
        Set maximum of the progressbar
        If delay is true the progressbar stays in endless mode until first step was done
        '''
        self.delayedmaximum = maximum
        if delay==False:
            self.progressBar.setMaximum(maximum)

    def step(self):
        '''
        Increment progress bar one step
        '''
        self.setMaximum(self.delayedmaximum, False)
        if self.progressBar.value() < 0:
            self.progressBar.setValue(1)
        else:
            self.progressBar.setValue(self.progressBar.value() + 1)

        self.computeRate()
        QApplication.processEvents()

    def computeRate(self):
        '''
          Compute the speed of operations (rolling average) after three seconds
        '''
        if not hasattr(self,'rate_update_next'):
            self.rate_update_frequency = 3
            self.rate_interval = 30

            #Set time for next calculation
            self.rate_update_next = QDateTime.currentDateTime().addSecs(self.rate_update_frequency)

            #Save time and value for calculation of rolling average
            self.rate_values = [{'time':QDateTime.currentDateTime(),'value':self.progressBar.value()}]

        elif QDateTime.currentDateTime() > self.rate_update_next:
            try:
                #Save value for calculation of rolling average
                currenttime = QDateTime.currentDateTime()
                currentvalue =  self.progressBar.value()

                #Remove old values
                if len(self.rate_values) > (self.rate_interval / self.rate_update_frequency):
                    self.rate_values = [v for v in self.rate_values if v['time'].secsTo(currenttime) <= self.rate_interval]

                #Add new value
                self.rate_values.append({'time':currenttime,'value':currentvalue})

                #Calculate rolling average
                timespan = self.rate_values[0]['time'].secsTo(self.rate_values[-1]['time'])
                valuespan = self.rate_values[-1]['value'] - self.rate_values[0]['value']

                rate = (valuespan * 60 / float(timespan))
                remainingseconds = round((self.progressBar.maximum() - self.progressBar.value()) / float(rate) * 60)
                remaining = timedelta(seconds=remainingseconds)
            except:
                rate = 0
                remaining = 0

            self.rate_update_next = QDateTime.currentDateTime().addSecs(self.rate_update_frequency)
            self.showInfo('rate',u"Completing {} nodes per minute".format(int(round(rate))))
            self.showInfo('remaining',u"Estimated remaining time is {}".format(str(remaining)))


    def showInfo(self,key,message):
        '''
          Show additional information in a label
          Label is updated when using the same key more the once
        '''

        if key in self.infos:
            widget = self.infos[key]
        else:
            widget = QLabel(message)
            self.infoPanel.addRow(widget)
            self.infos[key] = widget

        widget.setText(message)

