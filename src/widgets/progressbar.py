from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from datetime import timedelta

class ProgressBar(QDialog):

    def __init__(self, mainmessage, parent=None, hidden=False):
        #Init dialog
        super(ProgressBar, self).__init__(parent, Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(mainmessage)

        self.timeout = 60
        self.timer = None
        self.countdown = False
        self.autoRetry = False

        self.rate_update_frequency = 3
        self.rate_interval = 30
        self.rate_values = []

        self.wasRetried = False
        self.wasResumed = False

        #Create layout
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.errorLabel = QLabel()
        self.errorLabel.setStyleSheet('color: red; font-weight: bold;')
        self.errorLabel.hide()
        layout.addWidget(self.errorLabel)

        self.progressBar = QProgressBar()
        self.progressBar.setRange(0,0)
        layout.addWidget(self.progressBar,0)

        self.infoPanel = QVBoxLayout()
        #self.infoPanel.setRowWrapPolicy(QFormLayout.DontWrapRows)
        #self.infoPanel.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        #self.infoPanel.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        #self.infoPanel.setLabelAlignment(Qt.AlignLeft)
        self.infos = {}
        layout.addLayout(self.infoPanel)
        layout.addStretch(1)

        buttons = QDialogButtonBox()
        self.retryButton = QPushButton("Retry")
        self.retryButton.clicked.connect(self.doretry)
        buttons.addButton(self.retryButton, QDialogButtonBox.ActionRole)

        self.skipButton = QPushButton("Skip")
        self.skipButton.clicked.connect(self.doskip)
        buttons.addButton(self.skipButton, QDialogButtonBox.ActionRole)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancel)
        buttons.addButton(self.cancelButton,QDialogButtonBox.ActionRole)
        layout.addWidget(buttons)

        # set initial values
        self.wasCanceled = False

        #show
        if not hidden:
            self.open()
        self.hideError()

    def showError(self, msg, timeout=60, retry=False):
        if self.countdown == False:
            self.countdown = True
            self.wasResumed = False
            self.wasRetried = False
            self.autoRetry = retry
            self.timeout = timeout

            self.errorLabel.setText(msg)
            self.errorLabel.show()

            self.retryButton.setText("Retry")
            self.retryButton.show()

            self.skipButton.setText("Skip")
            self.skipButton.show()

            self.startCountdown()

    def hideError(self):
        self.countdown = False

        self.wasResumed = False
        self.wasRetried = False

        self.errorLabel.hide()
        self.retryButton.hide()
        self.skipButton.hide()

    def timerEvent(self):
        self.timeout -= 1
        if (self.timeout <= 0):
            if self.autoRetry:
                self.doretry()
            else:
                self.doskip()

        elif self.autoRetry:
            self.retryButton.setText("Retry [{}]".format(self.timeout))
            self.skipButton.setText("Skip")
            self.startCountdown()
        else:
            self.skipButton.setText("Skip [{}]".format(self.timeout))
            self.retryButton.setText("Retry")
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
        self.wasRetried = False
        self.wasResumed = True


    def doretry(self):
        self.stopCountdown()
        self.countdown = False
        self.timeout = 0
        self.wasRetried = True
        self.wasResumed = True


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
        return super(ProgressBar, self).close()

    def setValue(self, progress):
        '''
        set value of the progressbar
        '''
        self.setMaximum(self.delayedmaximum, False)
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
        QApplication.processEvents(maximumTime=10)

    def setRemaining(self ,n):
        self.showInfo('remainingnodes',"{} node(s) remaining.".format(n))
        self.progressBar.setValue(self.progressBar.maximum() - n)
        self.computeRate()

    def resetRate(self):
        self.rate_values = []

    def computeRate(self):
        '''
          Compute the speed of operations (rolling average) after three seconds
        '''

        # Save value for calculation of rolling average
        currenttime = QDateTime.currentDateTime()
        currentvalue = self.progressBar.value()

        if not hasattr(self,'rate_update_next'):
            #Set time for next calculation
            self.rate_update_next = QDateTime.currentDateTime().addSecs(self.rate_update_frequency)

        elif QDateTime.currentDateTime() > self.rate_update_next:
            #Remove old values
            if len(self.rate_values) > (self.rate_interval // self.rate_update_frequency):
                keep = ((self.rate_interval // self.rate_update_frequency) + 1)
                self.rate_values = self.rate_values[:keep]
                #self.rate_values = [v for v in self.rate_values if v['time'].secsTo(currenttime) <= self.rate_interval]

            #Add new value
            if (currentvalue >= 0) and ((len(self.rate_values) == 0) or (self.rate_values[-1]['value'] < currentvalue)):
                self.rate_values.append({'time':currenttime,'value':currentvalue})

            #Calculate rolling average
            if (len(self.rate_values) > 1) and (currentvalue > 0):
                timespan = self.rate_values[0]['time'].secsTo(currenttime)
                valuespan = currentvalue - self.rate_values[0]['value']

                if (valuespan > 0) and (timespan > 0):
                    rate = (valuespan * 60 / float(timespan))
                    remainingseconds = round((self.progressBar.maximum() - self.progressBar.value()) / float(rate) * 60)
                    remaining = timedelta(seconds=remainingseconds) if remainingseconds >= 0 else "lightyears"

                    self.showInfo('rate', "Completing {} nodes per minute".format(int(round(rate))))
                    self.showInfo('remaining', "Estimated remaining time is {}".format(str(remaining)))

            self.rate_update_next = QDateTime.currentDateTime().addSecs(self.rate_update_frequency)


    def showInfo(self,key,message):
        '''
          Show additional information in a label
          Label is updated when using the same key more the once
        '''

        if key in self.infos:
            widget = self.infos[key]
        else:
            widget = QLabel(message)
            self.infoPanel.addWidget(widget)
            self.infos[key] = widget

        widget.setText(message)


    def removeInfo(self,key):
        '''
          Remove additional information
        '''

        widget = self.infos.pop(key, None)
        if widget is not None:
            self.infoPanel.removeWidget(widget)
            widget.hide()
            widget.deleteLater()
            del widget
