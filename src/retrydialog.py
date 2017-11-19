from PySide.QtCore import *
from PySide.QtGui import *

class RetryDialog(QDialog):

    def __init__(self, message, timeout = 60, parent=None):
        super(RetryDialog, self).__init__(parent,Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)

        self.timeout = timeout

        self.setWindowTitle("Error")
        #self.setIcon(QMessageBox.Warning)

        #Create layout
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.msglabel = QLabel(message)
        layout.addWidget(self.msglabel)

        self.promtlabel = QLabel("Do you want to go on anyway?")
        layout.addWidget(self.promtlabel)

        buttons = QDialogButtonBox()
        self.yesButton = QPushButton(u"Yes [{}]".format(self.timeout))
        self.yesButton.clicked.connect(self.yes)
        buttons.addButton(self.yesButton,QDialogButtonBox.ActionRole)

        self.noButton = QPushButton(u"No")
        self.noButton.clicked.connect(self.no)
        buttons.addButton(self.noButton,QDialogButtonBox.ActionRole)

        layout.addWidget(buttons)

        #self.setDefaultButton(QMessageBox.No)

    def showEvent (self, event):
        QTimer().singleShot(1000, self.timerEvent)
        super(RetryDialog, self).showEvent(event)

    def timerEvent(self):
        self.timeout -= 1
        if (self.timeout <= 0):
            self.yes()
        else:
            self.yesButton.setText(u"Yes [{}]".format(self.timeout))
            QTimer().singleShot(1000, self.timerEvent)

    def yes(self):
        self.accept()
        #self.setResult(QDialog.Accepted)
        #self.close()

    def no(self):
        self.reject()

        #self.setResult(QDialog.Rejected)
        #self.close()

    # static method to create the dialog and return answer
    @staticmethod
    def doContinue(msg,timeout = 60,parent = None):
        dialog = RetryDialog(msg,timeout,parent)
        result = dialog.exec_()
        return result
