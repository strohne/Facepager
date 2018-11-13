from PySide.QtCore import *
from PySide.QtGui import *
from datetime import timedelta

class ProgressBar(QDialog):

    def __init__(self, mainmessage, parent=None):
        #Init dialog
        super(ProgressBar,self).__init__(parent,Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(mainmessage)

        self.timeout = 60
        self.timer = None
        self.countdown = False

        self.retry = False
        self.resume = False

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

        self.errorLabel = QLabel()
        self.errorLabel.setStyleSheet('color: red; font-weight: bold;')
        self.errorLabel.hide()
        layout.addWidget(self.errorLabel)

        buttons = QDialogButtonBox()
        self.retryButton = QPushButton(u"Retry")
        self.retryButton.clicked.connect(self.doretry)
        buttons.addButton(self.retryButton, QDialogButtonBox.ActionRole)

        self.skipButton = QPushButton(u"Skip")
        self.skipButton.clicked.connect(self.doskip)
        buttons.addButton(self.skipButton, QDialogButtonBox.ActionRole)

        self.cancelButton = QPushButton(u"Cancel")
        self.cancelButton.clicked.connect(self.cancel)
        buttons.addButton(self.cancelButton,QDialogButtonBox.ActionRole)
        layout.addWidget(buttons)

        # set initial values
        self.wasCanceled = False

        #show
        self.open()
        self.hideError()

    def showError(self, msg, timeout = 60, mode = "retry"):
        if self.countdown == False:
            self.countdown = mode
            self.resume = False
            self.retry = False
            self.timeout = timeout

            self.errorLabel.setText(msg)
            self.errorLabel.show()

            self.retryButton.setText(u"Retry")
            self.retryButton.show()
            self.skipButton.setText(u"Skip")
            self.skipButton.show()

            self.startCountdown()

    def hideError(self):
        self.countdown = False

        self.resume = False
        self.retry = False

        self.errorLabel.hide()
        self.retryButton.hide()
        self.skipButton.hide()

    def timerEvent(self):
        self.timeout -= 1
        if (self.timeout <= 0):
            if self.countdown == "retry":
                self.doretry()
            else:
                self.doskip()
        else:
            if self.countdown == "retry":
                self.retryButton.setText(u"Retry [{}]".format(self.timeout))
                self.skipButton.setText(u"Skip")
            else:
                self.skipButton.setText(u"Skip [{}]".format(self.timeout))
                self.retryButton.setText(u"Retry")

            self.startCountdown()

    def startCountdown(self):
        if self.timer is not None:
            self.timer.stop()

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timerEvent)
        self.timer.start()

    def stopCountdown(self):
        if self.timer is not None:
            self.timer.stop()

    def doskip(self):
        self.stopCountdown()
        self.countdown = False
        self.timeout = 0
        self.retry = False
        self.resume = True


    def doretry(self):
        self.stopCountdown()
        self.countdown = False
        self.timeout = 0
        self.retry = True
        self.resume = True


    def cancel(self):
        '''
        Set cancel flag, but doesn't close the dialog
        '''
        self.stopCountdown()
        self.countdown = False
        self.timeout = 0
        self.wasCanceled = True
        self.cancelButton.setText("Please wait...")
        self.cancelButton.setDisabled(True)


    def close(self):
        self.stopCountdown()
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

    def stepBack(self, n):
        self.progressBar.setValue(self.progressBar.value() - n)
        self.computeRate()

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

