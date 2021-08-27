from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
import os
import shutil
from tempfile import TemporaryDirectory
import re
import json
from widgets.textviewer import *
from urllib.parse import urlparse
import requests
import threading
import webbrowser
import platform
from widgets.dictionarytree import DictionaryTree
from widgets.progressbar import ProgressBar
from utilities import wraptip, formatdict

class PresetWindow(QDialog):
    logmessage = Signal(str)

    progressStart = Signal()
    progressShow = Signal()
    progressMax = Signal(int)
    progressStep = Signal()
    progressStop = Signal()

    def __init__(self, parent=None):
        super(PresetWindow,self).__init__(parent)

        self.mainWindow = parent
        self.setWindowTitle("Presets")
        self.setMinimumWidth(800);
        self.setMinimumHeight(600);

        #layout
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        #loading indicator
        self.loadingLock = threading.Lock()
        self.loadingIndicator = QLabel('Loading...please wait a second.')
        self.loadingIndicator.hide()
        layout.addWidget(self.loadingIndicator)

        #Middle
        central = QSplitter(self)
        layout.addWidget(central,1)

        #list view
        self.presetList = QTreeWidget(self)
        self.presetList.setHeaderHidden(True)
        self.presetList.setColumnCount(1)
        self.presetList.setIndentation(15)
        self.presetList.itemSelectionChanged.connect(self.currentChanged)
        central.addWidget(self.presetList)
        central.setStretchFactor(0, 0)

        # category / pipeline
        self.categoryWidget = QWidget()
        p = self.categoryWidget.palette()
        p.setColor(self.categoryWidget.backgroundRole(), Qt.white)
        self.categoryWidget.setPalette(p)
        self.categoryWidget.setAutoFillBackground(True)


        self.categoryLayout=QVBoxLayout()
        #self.categoryLayout.setContentsMargins(0, 0, 0, 0)
        self.categoryWidget.setLayout(self.categoryLayout)

        self.categoryView=QScrollArea()
        self.categoryView.setWidgetResizable(True)
        self.categoryView.setWidget(self.categoryWidget)
        central.addWidget(self.categoryView)
        central.setStretchFactor(1, 2)

        # Pipeline header
        self.pipelineName = QLabel('')
        self.pipelineName.setWordWrap(True)
        self.pipelineName.setStyleSheet("QLabel  {font-size:15pt;}")
        self.categoryLayout.addWidget(self.pipelineName)

        # Pipeline items
        # self.pipelineWidget = QTreeWidget()
        # self.pipelineWidget.setIndentation(0)
        # self.pipelineWidget.setUniformRowHeights(True)
        # self.pipelineWidget.setColumnCount(4)
        # self.pipelineWidget.setHeaderLabels(['Name','Module','Basepath','Resource'])
        # self.categoryLayout.addWidget(self.pipelineWidget)

        # preset widget
        self.presetWidget = QWidget()

        p = self.presetWidget.palette()
        p.setColor(self.presetWidget.backgroundRole(), Qt.white)
        self.presetWidget.setPalette(p)
        self.presetWidget.setAutoFillBackground(True)

        #self.presetWidget.setStyleSheet("background-color: rgb(255,255,255);")
        self.presetView=QScrollArea()
        self.presetView.setWidgetResizable(True)
        self.presetView.setWidget(self.presetWidget)

        central.addWidget(self.presetView)
        central.setStretchFactor(2, 2)

        #self.detailView.setFrameStyle(QFrame.Box)
        self.presetLayout=QVBoxLayout()
        self.presetWidget.setLayout(self.presetLayout)

        self.detailName = QLabel('')
        self.detailName.setWordWrap(True)
        self.detailName.setStyleSheet("QLabel  {font-size:15pt;}")

        self.presetLayout.addWidget(self.detailName)

        self.detailDescription = TextViewer()
        self.presetLayout.addWidget(self.detailDescription)


        self.presetForm=QFormLayout()
        self.presetForm.setRowWrapPolicy(QFormLayout.DontWrapRows);
        self.presetForm.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow);
        self.presetForm.setFormAlignment(Qt.AlignLeft | Qt.AlignTop);
        self.presetForm.setLabelAlignment(Qt.AlignLeft);
        self.presetLayout.addLayout(self.presetForm, 1)

        # Module
        self.detailModule = QLabel('')
        self.presetForm.addRow('<b>Module</b>', self.detailModule)

        #Options
        self.detailOptionsLabel = QLabel('<b>Options</b>')        
        self.detailOptionsLabel.setStyleSheet("QLabel {height:25px;}")
        self.detailOptions = TextViewer()
        self.presetForm.addRow(self.detailOptionsLabel, self.detailOptions)

        # Columns
        self.detailColumnsLabel = QLabel('<b>Columns</b>')        
        self.detailColumnsLabel.setStyleSheet("QLabel {height:25px;}")
        self.detailColumns = TextViewer()
        self.presetForm.addRow(self.detailColumnsLabel, self.detailColumns)

        # Speed
        self.detailSpeed = QLabel('')
        self.presetForm.addRow('<b>Speed</b>', self.detailSpeed)

        # Timeout
        self.detailTimeout = QLabel('')
        self.presetForm.addRow('<b>Timeout</b>', self.detailTimeout)

        # Max size
        self.detailMaxsize = QLabel('')
        self.presetForm.addRow('<b>Maximum size</b>', self.detailMaxsize)

        # Headers
        self.detailHeaders = QLabel('')
        self.presetForm.addRow('<b>Header nodes</b>', self.detailHeaders)
        
        # Buttons
        buttons= QHBoxLayout() #QDialogButtonBox()
        self.saveButton = QPushButton('New preset')
        self.saveButton.clicked.connect(self.newPreset)
        self.saveButton.setToolTip(wraptip("Create a new preset using the current tab and parameters"))
        #buttons.addButton(self.saveButton,QDialogButtonBox.ActionRole)
        buttons.addWidget(self.saveButton)

        self.overwriteButton = QPushButton('Edit preset')
        self.overwriteButton.clicked.connect(self.overwritePreset)
        self.overwriteButton.setToolTip(wraptip("Edit the selected preset."))
        #buttons.addButton(self.overwriteButton,QDialogButtonBox.ActionRole)
        buttons.addWidget(self.overwriteButton)

        self.deleteButton = QPushButton('Delete preset')
        self.deleteButton.clicked.connect(self.deletePreset)
        self.deleteButton.setToolTip(wraptip("Delete the selected preset. Default presets can not be deleted."))
        #buttons.addButton(self.deleteButton,QDialogButtonBox.ActionRole)
        buttons.addWidget(self.deleteButton)

        #layout.addWidget(buttons,1)

        buttons.addStretch()

        self.reloadButton=QPushButton('Reload')
        self.reloadButton.clicked.connect(self.reloadPresets)
        self.reloadButton.setToolTip(wraptip("Reload all preset files."))
        buttons.addWidget(self.reloadButton)

        self.rejectButton=QPushButton('Cancel')
        self.rejectButton.clicked.connect(self.close)
        self.rejectButton.setToolTip(wraptip("Close the preset dialog."))
        buttons.addWidget(self.rejectButton)

        self.columnsButton=QPushButton('Add Columns')
        self.columnsButton.setDefault(True)
        self.columnsButton.clicked.connect(self.addColumns)
        self.columnsButton.setToolTip(wraptip("Add the columns of the selected preset to the column setup."))
        buttons.addWidget(self.columnsButton)

        self.applyButton=QPushButton('Apply')
        self.applyButton.setDefault(True)
        self.applyButton.clicked.connect(self.applyPreset)
        self.applyButton.setToolTip(wraptip("Load the selected preset."))
        buttons.addWidget(self.applyButton)

        layout.addLayout(buttons)

        #status bar
        self.statusbar = QStatusBar()
        #self.folderLabel = QLabel("")
        self.folderButton = QPushButton("")
        self.folderButton.setFlat(True)
        self.folderButton.clicked.connect(self.statusBarClicked)
        self.statusbar.insertWidget(0,self.folderButton)
        layout.addWidget(self.statusbar)


        #self.presetFolder = os.path.join(os.path.dirname(self.mainWindow.settings.fileName()),'presets')
        self.presetFolder = os.path.join(os.path.expanduser("~"),'Facepager','Presets')
        self.presetFolderDefault = os.path.join(os.path.expanduser("~"),'Facepager','DefaultPresets')
        self.folderButton.setText(self.presetFolder)

        self.presetsDownloaded = False
        self.presetSuffix = ['.3_9.json','.3_10.json','.fp4.json']
        self.lastSelected = None

        # Progress bar (sync with download thread by signals
        self.progress = ProgressBar("Downloading default presets from GitHub...", self, hidden=True)
        self.progressStart.connect(self.setProgressStart)
        self.progressShow.connect(self.setProgressShow)
        self.progressMax.connect(self.setProgressMax)
        self.progressStep.connect(self.setProgressStep)
        self.progressStop.connect(self.setProgressStop)
#         if getattr(sys, 'frozen', False):
#             self.defaultPresetFolder = os.path.join(os.path.dirname(sys.executable),'presets')
#         elif __file__:
#             self.defaultPresetFolder = os.path.join(os.path.dirname(__file__),'presets')

    # Sycn progress bar with download thread
    @Slot()
    def setProgressStart(self):
        if self.progress is None:
            self.progress = ProgressBar("Downloading default presets from GitHub...", self, hidden=True)

    def setProgressShow(self):
        if self.progress is not None:
            self.progress.setModal(True)
            self.progress.show()
        QApplication.processEvents()

    def setProgressMax(self, maximum):
        if self.progress is not None:
            self.progress.setMaximum(maximum)

    def setProgressStep(self):
        if self.progress is not None:
            self.progress.step()

    def setProgressStop(self):
        self.progress.close()
        self.progress = None

    def statusBarClicked(self):
        if not os.path.exists(self.presetFolder):
            os.makedirs(self.presetFolder)

        if platform.system() == "Windows":
            webbrowser.open(self.presetFolder)
        elif platform.system() == "Darwin":
            webbrowser.open('file:///'+self.presetFolder)
        else:
            webbrowser.open('file:///'+self.presetFolder)


    def currentChanged(self):
        #hide
        self.detailName.setText("")
        self.detailModule.setText("")
        self.detailDescription.setText("")
        self.detailOptions.setText("")
        self.detailColumns.setText("")

        self.presetView.hide()
        self.categoryView.hide()

        current = self.presetList.currentItem()
        if current and current.isSelected():
            data = current.data(0,Qt.UserRole)

            # Single preset
            if not data.get('iscategory',False):
                self.lastSelected = os.path.join(data.get('folder',''),data.get('filename',''))

                self.detailName.setText(data.get('name'))
                self.detailModule.setText(data.get('module'))
                self.detailDescription.setText(data.get('description')+"\n")
                self.detailOptions.setHtml(formatdict(data.get('options',[])))
                self.detailColumns.setText("\r\n".join(data.get('columns', [])))
                self.detailSpeed.setText(str(data.get('speed','')))
                self.detailTimeout.setText(str(data.get('timeout', '')))
                self.detailMaxsize.setText(str(data.get('maxsize', '')))

                #self.applyButton.setText("Apply")
                self.presetView.show()

            # Category
            else:
#                self.pipelineName.setText(str(data.get('category')))

#                 self.pipelineWidget.clear()
#                 for i in range(current.childCount()):
#                     presetitem = current.child(i)
#                     preset = presetitem.data(0, Qt.UserRole)
#
#                     treeitem = QTreeWidgetItem(self.pipelineWidget)
#                     treeitem.setText(0,preset.get('name'))
#                     treeitem.setText(1, preset.get('module'))
#                     treeitem.setText(2, getDictValue(preset,'options.basepath'))
#                     treeitem.setText(3, getDictValue(preset,'options.resource'))
# #                   treeitem.setText(4, preset.get('description'))
#
#                     self.pipelineWidget.addTopLevelItem(treeitem)

                #self.applyButton.setText("Run pipeline")
                self.categoryView.show()

    def showPresets(self):
        self.clear()
        self.show()
        QApplication.processEvents()

        self.progressShow.emit()

        self.initPresets()
        self.raise_()


    def addPresetItem(self,folder,filename,default=False,online=False):
        try:
            if online:
                data= requests.get(folder+filename).json()
            else:
                with open(os.path.join(folder, filename), 'r', encoding="utf-8") as input:
                    data = json.load(input)

            data['filename'] = filename
            data['folder'] = folder
            data['default'] = default
            data['online'] = online

            if data.get('type','preset') == 'pipeline':
                data['category'] = data.get('category', 'noname')
                if not data['category'] in self.categoryNodes:
                    categoryItem = PresetWidgetItem()
                    categoryItem.setText(0, data['category'])

                    ft = categoryItem.font(0)
                    ft.setWeight(QFont.Bold)
                    categoryItem.setFont(0, ft)

                    self.presetList.addTopLevelItem(categoryItem)
                else:
                    categoryItem = self.categoryNodes[data['category']]

                data['iscategory'] = True
                categoryItem.setData(0, Qt.UserRole,data)

            else:
                data['caption'] = data.get('name')
                if default:
                    data['caption'] = data['caption'] +" *"

                data['category'] = data.get('category','')
                if (data['category'] == ''):
                    if (data.get('module') in ['Generic','Files']):
                        try:
                            data['category'] = data.get('module') + " ("+urlparse(data['options']['basepath']).netloc+")"
                        except:
                            data['category'] = data.get('module')
                    else:
                        data['category'] = data.get('module')


                if not data['category'] in self.categoryNodes:
                    categoryItem = PresetWidgetItem()
                    categoryItem.setText(0,data['category'])

                    ft = categoryItem.font(0)
                    ft.setWeight(QFont.Bold)
                    categoryItem.setFont(0,ft)

                    categoryItem.setData(0,Qt.UserRole,{'iscategory':True,'name':data['module'],'category':data['category']})

                    self.presetList.addTopLevelItem(categoryItem)
                    self.categoryNodes[data['category']] = categoryItem

                else:
                    categoryItem = self.categoryNodes[data['category']]

                newItem = PresetWidgetItem()
                newItem.setText(0,data['caption'])
                newItem.setData(0,Qt.UserRole,data)
                if default:
                    newItem.setForeground(0,QBrush(QColor("darkblue")))
                categoryItem.addChild(newItem)

            #self.presetList.setCurrentItem(newItem,0)
            QApplication.processEvents()

            return newItem

        except Exception as e:
             QMessageBox.information(self,"Facepager","Error loading preset:"+str(e))
             return None

    def clear(self):
        self.presetList.clear()
        self.presetView.hide()
        self.categoryView.hide()
        self.loadingIndicator.show()

    def checkDefaultFiles(self):
        if not os.path.exists(self.presetFolderDefault):
            self.downloadDefaultFiles()
        elif len(os.listdir(self.presetFolderDefault)) == 0:
            self.downloadDefaultFiles()

    def downloadDefaultFiles(self, silent=False):
        with self.loadingLock:
            if self.presetsDownloaded:
                return False

            # Progress
            self.progressStart.emit()
            if not silent:
                self.progressShow.emit()

            # Create temporary download folder
            tmp = TemporaryDirectory(suffix='FacepagerDefaultPresets')
            try:
                #Download
                files = requests.get("https://api.github.com/repos/strohne/Facepager/contents/presets").json()
                files = [f['path'] for f in files if f['path'].endswith(tuple(self.presetSuffix))]
                self.progressMax.emit(len(files))

                for filename in files:
                    response = requests.get("https://raw.githubusercontent.com/strohne/Facepager/master/"+filename)
                    if response.status_code != 200:
                        raise(f"GitHub is not available (status code {response.status_code})")
                    with open(os.path.join(tmp.name, os.path.basename(filename)), 'wb') as f:
                        f.write(response.content)

                    self.progressStep.emit()

                #Create folder
                if not os.path.exists(self.presetFolderDefault):
                    os.makedirs(self.presetFolderDefault)

                #Clear folder
                for filename in os.listdir(self.presetFolderDefault):
                    os.remove(os.path.join(self.presetFolderDefault,filename))

                # Move files from tempfolder
                for filename in os.listdir(tmp.name):
                    shutil.move(os.path.join(tmp.name,filename), self.presetFolderDefault)

                self.logmessage.emit("Default presets downloaded from GitHub.")
            except Exception as e:
                if not silent:
                    QMessageBox.information(self,"Facepager","Error downloading default presets:"+str(e))
                self.logmessage.emit("Error downloading default presets:" + str(e))
                return False
            else:
                self.presetsDownloaded = True
                return True
            finally:
                tmp.cleanup()
                self.progressStop.emit()

    def reloadPresets(self):
        self.presetsDownloaded = False
        self.downloadDefaultFiles()
        self.initPresets()

    def initPresets(self):
        self.loadingIndicator.show()

        #self.defaultPresetFolder
        self.categoryNodes = {}
        self.presetList.clear()
        self.presetView.hide()
        self.categoryView.hide()

        selectitem = None

        while not self.presetsDownloaded:
            QApplication.processEvents()

        if os.path.exists(self.presetFolderDefault):
            files = [f for f in os.listdir(self.presetFolderDefault) if f.endswith(tuple(self.presetSuffix))]
            for filename in files:
                newitem = self.addPresetItem(self.presetFolderDefault,filename,True)
                if self.lastSelected is not None and (self.lastSelected == os.path.join(self.presetFolderDefault,filename)):
                    selectitem = newitem

        if os.path.exists(self.presetFolder):
            files = [f for f in os.listdir(self.presetFolder) if f.endswith(tuple(self.presetSuffix))]
            for filename in files:
                newitem = self.addPresetItem(self.presetFolder,filename)
                if self.lastSelected is not None and (self.lastSelected == str(os.path.join(self.presetFolder,filename))):
                    selectitem = newitem

        #self.presetList.expandAll()
        self.presetList.setFocus()
        self.presetList.sortItems(0,Qt.AscendingOrder)

        selectitem = self.presetList.topLevelItem(0) if selectitem is None else selectitem
        self.presetList.setCurrentItem(selectitem)

        self.applyButton.setDefault(True)
        self.loadingIndicator.hide()

    def getCategories(self):
        categories = []

        root = self.presetList.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            data = item.data(0, Qt.UserRole)
            categories.append(data.get('category', ''))

        return categories

    def startPipeline(self):
        if not self.presetList.currentItem():
            return False

        # Get category item
        root_item = self.presetList.currentItem()
        root_data = root_item.data(0, Qt.UserRole)
        if not root_data.get('iscategory', False):
            root_item = root_item.parent()
            root_data = root_item.data(0, Qt.UserRole)

        # Create pipeline
        pipeline = []

        for i in range(root_item.childCount()):
            item = root_item.child(i)

            preset = item.data(0, Qt.UserRole)
            module = self.mainWindow.getModule(preset.get('module', None))
            options = module.getSettings()
            options.update(preset.get('options', {}))
            preset['options'] = options.copy()
            preset['item'] = item

            pipeline.append(preset)

        # Process pipeline
        return self.mainWindow.apiActions.queryPipeline(pipeline)
        #self.close()


    def applyPreset(self):
        if not self.presetList.currentItem():
            return False

        data = self.presetList.currentItem().data(0,Qt.UserRole)
        if data.get('iscategory',False):
            return False
            #self.startPipeline()
        else:
            self.mainWindow.apiActions.applySettings(data)

        self.close()

    def addColumns(self):
        if not self.presetList.currentItem():
            return False

        data = self.presetList.currentItem().data(0,Qt.UserRole)
        if not data.get('iscategory',False):
            self.mainWindow.apiActions.addColumns(data)


    def uniqueFilename(self,name):
        filename = re.sub('[^a-zA-Z0-9_-]+', '_', name )+self.presetSuffix[-1]
        i = 1
        while os.path.exists(os.path.join(self.presetFolder, filename)) and i < 10000:
            filename = re.sub('[^a-zA-Z0-9_-]+', '_', name )+"-"+str(i)+self.presetSuffix[-1]
            i+=1

        if os.path.exists(os.path.join(self.presetFolder, filename)):
            raise Exception('Could not find unique filename')
        return filename

    def deletePreset(self):
        if not self.presetList.currentItem():
            return False
        data = self.presetList.currentItem().data(0,Qt.UserRole)
        if data.get('default',False):
            QMessageBox.information(self,"Facepager","Cannot delete default presets.")
            return False

        if data.get('iscategory',False):
            return False

        reply = QMessageBox.question(self, 'Delete Preset',"Are you sure to delete the preset \"{0}\"?".format(data.get('name','')), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return False

        os.remove(os.path.join(self.presetFolder, data.get('filename')))
        self.initPresets()

    def editPreset(self,data = None):
        dialog=QDialog(self.mainWindow)

        self.currentData = data if data is not None else {}
        self.currentFilename = self.currentData.get('filename',None)

        if self.currentFilename is None:
            dialog.setWindowTitle("New Preset")
        else:
            dialog.setWindowTitle("Edit selected preset")

        layout=QVBoxLayout()
        label=QLabel("<b>Name</b>")
        layout.addWidget(label)
        name=QLineEdit()
        name.setText(self.currentData.get('name',''))
        layout.addWidget(name,0)

        label=QLabel("<b>Category</b>")
        layout.addWidget(label)
        category= QComboBox(self)
        category.addItems(self.getCategories())
        category.setEditable(True)

        category.setCurrentText(self.currentData.get('category',''))
        layout.addWidget(category,0)


        label=QLabel("<b>Description</b>")
        layout.addWidget(label)
        description=QTextEdit()
        description.setMinimumWidth(500)
        description.acceptRichText=False
        description.setPlainText(self.currentData.get('description',''))
        description.setFocus()
        layout.addWidget(description,1)


        overwriteLayout =QHBoxLayout()
        self.overwriteCheckbox = QCheckBox(self)
        self.overwriteCheckbox.setCheckState(Qt.Unchecked)
        overwriteLayout.addWidget(self.overwriteCheckbox)
        label=QLabel("<b>Overwrite parameters with current settings</b>")
        overwriteLayout.addWidget(label)
        overwriteLayout.addStretch()

        if self.currentFilename is not None:
            layout.addLayout(overwriteLayout)

        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        layout.addWidget(buttons,0)
        dialog.setLayout(layout)

        def save():
            data_meta = {
                    'name':name.text(),
                    'category':category.currentText(),
                    'description':description.toPlainText()
            }

            data_settings = self.mainWindow.apiActions.getPresetOptions()
            self.currentData.update(data_meta)

            if self.currentFilename is None:
                self.currentData.update(data_settings)

            elif self.overwriteCheckbox.isChecked():
                reply = QMessageBox.question(self, 'Overwrite Preset',"Are you sure to overwrite the selected preset \"{0}\" with the current settings?".format(data.get('name','')), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply != QMessageBox.Yes:
                    dialog.close()
                    self.currentFilename = None
                    return False
                else:
                    self.currentData.update(data_settings)

            # Sanitize and reorder
            keys = ['name', 'category', 'description', 'module', 'options', 'speed', 'saveheaders','timeout','maxsize','columns']
            self.currentData = {k: self.currentData.get(k, None) for k in keys}

            # Create folder
            if not os.path.exists(self.presetFolder):
                os.makedirs(self.presetFolder)

            # Remove old file
            if self.currentFilename is not None:
                filepath = os.path.join(self.presetFolder, self.currentFilename)
                if os.path.exists(filepath):
                    os.remove(filepath)

            # Save new file
            catname = category.currentText() if category.currentText() != "" else self.mainWindow.RequestTabs.currentWidget().name
            self.currentFilename = self.uniqueFilename(catname+"-"+name.text())

            with open(os.path.join(self.presetFolder,self.currentFilename), 'w') as outfile:
                json.dump(self.currentData, outfile,indent=2, separators=(',', ': '))

            dialog.close()
            return True

        def close():
            dialog.close()
            self.currentFilename = None
            return False

        #connect the nested functions above to the dialog-buttons
        buttons.accepted.connect(save)
        buttons.rejected.connect(close)
        dialog.exec()
        return self.currentFilename


    def newPreset(self):
        filename = self.editPreset()
        if filename is not None:
            newitem = self.addPresetItem(self.presetFolder,filename)
            self.presetList.sortItems(0,Qt.AscendingOrder)
            self.presetList.setCurrentItem(newitem,0)


    def overwritePreset(self):
        if not self.presetList.currentItem():
            return False

        item = self.presetList.currentItem()
        data = item.data(0,Qt.UserRole)

        if data.get('default',False):
            QMessageBox.information(self,"Facepager","Cannot edit default presets.")
            return False

        if data.get('iscategory',False):
            return False

        filename = self.editPreset(data)

        if filename is not None:
            item.parent().removeChild(item)
            item = self.addPresetItem(self.presetFolder,filename)

            self.presetList.sortItems(0,Qt.AscendingOrder)
            self.presetList.setCurrentItem(item,0)

class PresetWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        data1 = self.data(0,Qt.UserRole)
        data2 = other.data(0,Qt.UserRole)

        if data1.get('iscategory') and data2.get('iscategory'):
            #order = ['Facebook','YouTube','Twitter','Twitter Streaming','Amazon','Files','Generic']
            # if data1.get('name','') in order and data2.get('name','') in order:
            #     if data1.get('name','') == data2.get('name',''):
            #         return data1.get('category','') < data2.get('category','')
            #     else:
            #         return order.index(data1.get('name','')) < order.index(data2.get('name',''))
            #
            # elif (data1.get('name','') in order) != (data2.get('name','') in order):
            #     return data1.get('name','') in order
            # else:
            return data1.get('category','').lower()  < data2.get('category','').lower()
        elif data1.get('default',False) != data2.get('default',False):
            return data1.get('default',False)
        else:
            return data1.get('name','').lower() < data2.get('name','').lower()
