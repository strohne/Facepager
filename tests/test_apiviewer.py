from unittest import TestCase
from PySide2.QtWidgets import QMainWindow
from dialogs.apiviewer import ApiViewer

class Test_Utilities(TestCase):

    def setUp(self):
        self.mainwindow = QMainWindow()
        self.apiviewer = ApiViewer(self.mainwindow)

    def tearDown(self):
        del self.apiviewer
        del self.mainwindow

    def test_get_api_doc(self):
        pass

        # out = self.apiviewer.getApiDoc("Facebook")
        # self.assertEqual('Facebook',out['x-facepager-module'])
        # self.assertEqual('https://graph.facebook.com/v3.3', out['servers'][0]['url'])
