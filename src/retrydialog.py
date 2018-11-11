from PySide.QtCore import *
from PySide.QtGui import *

class RetryDialog(QDialog):

    def __init__(self, message, timeout = 60, parent=None, retry=False):
        super(RetryDialog, self).__init__(parent,Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)

        self.timeout = timeout
        self.retry = retry

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

        self.retryButton = QPushButton(u"Retry")
        self.retryButton.clicked.connect(self.doretry)
        buttons.addButton(self.retryButton, QDialogButtonBox.ActionRole)

        self.continueButton = QPushButton(u"Continue")
        self.continueButton.clicked.connect(self.docontinue)
        buttons.addButton(self.continueButton, QDialogButtonBox.ActionRole)

        self.noButton = QPushButton(u"Cancel")
        self.noButton.clicked.connect(self.no)
        buttons.addButton(self.noButton,QDialogButtonBox.ActionRole)

        layout.addWidget(buttons)

        if retry:
            self.retryButton.setFocus()
        else:
            self.continueButton.setFocus()

        #self.setDefaultButton(QMessageBox.No)

    def showEvent (self, event):
        QTimer().singleShot(1000, self.timerEvent)
        super(RetryDialog, self).showEvent(event)

    def timerEvent(self):
        self.timeout -= 1
        if (self.timeout <= 0):
            self.accept()
        else:
            if self.retry:
                self.retryButton.setText(u"Retry [{}]".format(self.timeout))
                self.continueButton.setText(u"Continue")
            else:
                self.continueButton.setText(u"Continue [{}]".format(self.timeout))
                self.retryButton.setText(u"Retry")

            QTimer().singleShot(1000, self.timerEvent)

    def docontinue(self):
        self.retry = False
        self.accept()

    def doretry(self):
        self.retry = True
        self.accept()

    def no(self):
        self.retry = False
        self.reject()

        #self.setResult(QDialog.Rejected)
        #self.close()

    # static method to create the dialog and return answer
    @staticmethod
    def doContinue(msg,timeout = 60,parent = None, retry = False):
        dialog = RetryDialog(msg, timeout, parent, retry)
        result = dialog.exec_()
        return (result, dialog.retry)
