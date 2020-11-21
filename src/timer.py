from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

#states
TIMER_INACTIVE = 0
TIMER_ACTIVE = 1
TIMER_COUNTDOWN = 2
#TIMER_WAITING = 3
TIMER_FIRED = 4

class TimerWindow(QDialog):
    
    #signals
    timerstarted = Signal(QDateTime)    
    timercountdown = Signal(int)
    #timerwaiting = Signal(int)
    timerfired = Signal(list)
    timerstopped = Signal()
    

    
    def __init__(self, parent=None):
        super(TimerWindow,self).__init__(parent)
        
        self.mainWindow = parent
        self.setWindowTitle("Timer")
        
        #state
        self.state = TIMER_INACTIVE
        self.firetime = False
        self.interval = False
        self.remaining = 0
        self.data = {}
        self.nextdata = {}
        
        #timer
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.onFire)
        
        #layout
        layout = QVBoxLayout()
        central = QHBoxLayout()
        layout.addLayout(central,1)
        self.setLayout(layout)
        
        settingsLayout=QFormLayout()
        central.addLayout(settingsLayout,1)
        

        
        #Start time
        self.startTimeEdit = QDateTimeEdit(QTime.currentTime())
        self.startTimeEdit.setDisplayFormat("hh:mm")
        settingsLayout.addRow("Start Time (hh:mm)",self.startTimeEdit)
        
        #Interval
        intervalLayout = QHBoxLayout()

        self.intervalHoursEdit = QSpinBox(self)
        self.intervalHoursEdit.setMinimum(0)
        self.intervalHoursEdit.setValue(0)
        intervalLayout.addWidget(self.intervalHoursEdit)
        intervalLayout.addWidget(QLabel('hours'))

        self.intervalMinutesEdit = QSpinBox(self)
        self.intervalMinutesEdit.setMinimum(0)
        self.intervalMinutesEdit.setMaximum(59)
        self.intervalMinutesEdit.setValue(10)

        intervalLayout.addWidget(self.intervalMinutesEdit)
        intervalLayout.addWidget(QLabel('minutes'))

        settingsLayout.addRow("Interval", intervalLayout)

        #buttons
        buttons=QDialogButtonBox()
        self.startTimerButton = QPushButton('Start Timer')        
        self.startTimerButton.clicked.connect(self.startTimerClicked)
        buttons.addButton(self.startTimerButton,QDialogButtonBox.ActionRole)
        
        self.stopTimerButton = QPushButton('Stop Timer')        
        self.stopTimerButton.clicked.connect(self.stopTimerClicked)
        buttons.addButton(self.stopTimerButton,QDialogButtonBox.ActionRole)
       
        buttons.addButton(QDialogButtonBox.Cancel)
        buttons.rejected.connect(self.close)                        
        layout.addWidget(buttons,0)

    def setupTimer(self,data):                
        self.nextdata = data

        time = QTime.currentTime()        
        self.startTimeEdit.setTime(QTime(time.hour(), time.minute()))
        
        self.stopTimerButton.setEnabled(self.state != TIMER_INACTIVE)

        self.exec_()
        
    def cancelTimer(self):
        self.timer.stop()
        self.state = TIMER_INACTIVE
        self.timerstopped.emit()
        
    def startTimerClicked(self):
        self.cancelTimer()
        self.data = self.nextdata

        self.interval = self.intervalHoursEdit.value() * 60 * 60 + self.intervalMinutesEdit.value() * 60
        if self.interval == 0:
            return False

        self.firetime = QDateTime.currentDateTime()
        self.firetime.setTime(self.startTimeEdit.time())

        self.updateTimer()
        self.close()

    def stopTimerClicked(self):
        self.cancelTimer()        
        self.close()

    def onFire(self):
        if (self.state != TIMER_INACTIVE):
            self.updateTimer()

    def calcFiretime(self):
        while (QDateTime.currentDateTime().addSecs(5) > self.firetime):
            self.firetime = self.firetime.addSecs(self.interval)             
                    
    def updateTimer(self):
        self.remaining = max(0, QDateTime.currentDateTime().secsTo(self.firetime))
                
        if  (self.remaining == 0):
            self.state = TIMER_FIRED            
            self.timerfired.emit(self.data)
            
            self.calcFiretime()
            self.updateTimer()

        elif  (self.remaining < 10):
            self.state = TIMER_COUNTDOWN
            self.timercountdown.emit(self.remaining)
            self.timer.start(1000)
            
        else:
            self.state = TIMER_ACTIVE
            self.timer.start((self.remaining - 10) * 1000)
            self.timerstarted.emit(self.firetime)
