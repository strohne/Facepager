from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtGui import *

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
        layout = QVBoxLayout(self)        
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
        self.intervalTimeEdit = QDateTimeEdit(QTime(0,5))
        self.intervalTimeEdit.setDisplayFormat("hh:mm")
        self.intervalTimeEdit.setMinimumTime(QTime(0,1))
        settingsLayout.addRow("Interval (hh:mm)",self.intervalTimeEdit)

        #Nodes
        self.nodeCount = QLabel("0")
        settingsLayout.addRow("Node Count",self.nodeCount)
        
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
        self.nodeCount.setText(str(data.get('nodecount',0)))
        time = QTime.currentTime()        
        self.startTimeEdit.setTime(QTime(time.hour(),time.minute()))
        
        self.stopTimerButton.setEnabled(self.state != TIMER_INACTIVE)
        self.startTimerButton.setEnabled(data.get('nodecount',0) > 0)
              
        self.exec_()
        
    def cancelTimer(self):
        self.timer.stop()
        self.state = TIMER_INACTIVE
        self.timerstopped.emit()
        
    def startTimerClicked(self):
        if self.nextdata.get('nodecount',0) > 0:
            self.cancelTimer()
            self.data = self.nextdata
            self.interval = self.intervalTimeEdit.time().minute() * 60 + self.intervalTimeEdit.time().second()
            self.firetime = QDateTime.currentDateTime()
            self.firetime.setTime(self.startTimeEdit.time())
            #self.calcFiretime()
            self.updateTimer()
            self.close()

    def stopTimerClicked(self):
        self.cancelTimer()        
        self.close()

    def onFire(self):
        if (self.state != TIMER_INACTIVE): self.updateTimer()

    def calcFiretime(self):
        while (QDateTime.currentDateTime().addSecs(5) > self.firetime):
            self.firetime = self.firetime.addSecs(self.interval)             
                    
    def updateTimer(self):
        self.remaining = max(0,QDateTime.currentDateTime().secsTo(self.firetime)+1)
                
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
            
