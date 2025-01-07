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
from utilities import *
from settings import settings

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
        self.pipelineWidget = QTreeWidget()
        self.pipelineWidget.setIndentation(0)
        self.pipelineWidget.setUniformRowHeights(True)
        self.pipelineWidget.setColumnCount(4)
        self.pipelineWidget.setHeaderLabels(['Name','Module','Basepath','Resource'])
        self.categoryLayout.addWidget(self.pipelineWidget)

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
        buttons= QHBoxLayout()

        self.saveButton = QPushButton('New preset')
        self.saveButton.clicked.connect(self.newPreset)
        self.saveButton.setToolTip(wraptip("Create a new preset using the current tab and parameters"))
        buttons.addWidget(self.saveButton)

        self.newPipelineButton = QPushButton('New pipeline')
        self.newPipelineButton.clicked.connect(self.newPipeline)
        self.newPipelineButton.setToolTip(wraptip("Create a new pipeline"))
        buttons.addWidget(self.newPipelineButton)

        self.overwriteButton = QPushButton('Edit')
        self.overwriteButton.clicked.connect(self.overwritePreset)
        self.overwriteButton.setToolTip(wraptip("Edit the selected preset or pipeline."))
        buttons.addWidget(self.overwriteButton)

        self.deleteButton = QPushButton('Delete')
        self.deleteButton.clicked.connect(self.deletePreset)
        self.deleteButton.setToolTip(wraptip("Delete the selected preset or pipeline. Default items can not be deleted."))
        buttons.addWidget(self.deleteButton)

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
        self.presetsDownloaded = True
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
        self.hideDetails()

        current = self.presetList.currentItem()
        if not current or not current.isSelected():
            return

        data = current.data(0,Qt.UserRole)
        itemType = data.get('type', 'preset')

        # Single preset
        if itemType == 'preset':
            self.lastSelected = os.path.join(data.get('folder',''),data.get('filename',''))

            self.detailName.setText(data.get('name'))
            self.detailModule.setText(data.get('module'))
            self.detailDescription.setText(data.get('description', '')+"\n")
            self.detailOptions.setHtml(formatdict(data.get('options',[])))
            self.detailColumns.setText("\r\n".join(data.get('columns', [])))
            self.detailSpeed.setText(str(data.get('speed','')))
            self.detailTimeout.setText(str(data.get('timeout', '')))
            self.detailMaxsize.setText(str(data.get('maxsize', '')))

            self.applyButton.setText("Apply")
            self.presetView.show()

        # Category
        elif itemType == 'pipeline':
            self.pipelineName.setText(str(data.get('name')))

            self.pipelineWidget.clear()
            for i in range(current.childCount()):
                presetitem = current.child(i)
                preset = presetitem.data(0, Qt.UserRole)

                treeitem = QTreeWidgetItem(self.pipelineWidget)
                treeitem.setText(0,preset.get('name'))
                treeitem.setText(1, preset.get('module'))
                treeitem.setText(2, getDictValue(preset,'options.basepath'))
                treeitem.setText(3, getDictValue(preset,'options.resource'))
                # treeitem.setText(4, preset.get('description'))

                self.pipelineWidget.addTopLevelItem(treeitem)

            self.applyButton.setText("Run pipeline")
            self.categoryView.show()

    def showPresets(self):
        self.clear()
        self.show()
        QApplication.processEvents()

        self.progressShow.emit()

        self.initPresets()
        self.raise_()


    def addCategoryItem(self, data, default):
        """
        Add a category item if it does not exist, otherwise return the existing item

        :param data: A dict with the keys module and category
        :return: A PresetWidgetItem() with the iscategory property set to True
        """
        module = data.get('module')
        category = data.get('category')

        if not category in self.categoryNodes:
            categoryItem = PresetWidgetItem()
            categoryItem.setText(0, category)

            ft = categoryItem.font(0)
            ft.setWeight(QFont.Bold)
            categoryItem.setFont(0, ft)

            categoryItem.setData(0, Qt.UserRole,
                                 {'iscategory': True, 'name': module, 'category': category, 'type': 'category'})

            self.presetList.addTopLevelItem(categoryItem)
            self.categoryNodes[category] = categoryItem

        else:
            categoryItem = self.categoryNodes[category]

        return categoryItem

    def addPresetItem(self, parentItem, data, default):
        data['type'] = 'preset'
        data['caption'] = data.get('name')
        if default:
            data['caption'] = data['caption'] + " *"

        newItem = PresetWidgetItem()
        newItem.setText(0, data['caption'])
        newItem.setData(0, Qt.UserRole, data)
        if default:
            newItem.setForeground(0, QBrush(QColor("darkblue")))

        parentItem.addChild(newItem)

        return newItem

    def addPipelineItem(self, parentItem, data, default):
        if data.get('type','preset') == 'pipeline':
            pipelineData = data
            pipelineData['category'] = data.get('category', 'No category')
            pipelineData['caption'] = data.get('name', '')
        else:
            pipelineData = {}
            pipelineData['category'] = data.get('category','No category')
            pipelineData['caption'] = data.get('pipeline','')

        if default:
            pipelineData['caption'] = pipelineData['caption'] + " *"

        if not pipelineData['category'] in self.pipelineNodes:
            self.pipelineNodes[pipelineData['category']] = {}
        pipelineCategory = self.pipelineNodes[pipelineData['category']]

        if not pipelineData['caption'] in pipelineCategory:
            pipelineItem = PresetWidgetItem()
            pipelineItem.setText(0, pipelineData['caption'])
            if default:
                pipelineItem.setForeground(0, QBrush(QColor("darkblue")))
            pipelineItem.setData(0, Qt.UserRole, pipelineData)
            parentItem.addChild(pipelineItem)
            pipelineCategory[pipelineData['caption']] = pipelineItem
        else:
            pipelineItem = pipelineCategory[pipelineData['caption']]
            if data.get('type', 'preset') == 'pipeline':
                pipelineItem.setData(0, Qt.UserRole, pipelineData)

        return pipelineItem

    def addItem(self,folder,filename,default=False,online=False):
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
            data['type'] = data.get('type', 'preset')

            # First level: category
            data['category'] = data.get('category', 'No category')
            if (data['category'] == ''):
                if (data.get('module') in ['Generic', 'Files']):
                    try:
                        data['category'] = data.get('module') + " (" + urlparse(
                            data['options']['basepath']).netloc + ")"
                    except:
                        data['category'] = data.get('module')
                else:
                    data['category'] = data.get('module')

            categoryItem = self.addCategoryItem(data, default)

            # Pipelines on second level
            if data.get('pipeline', '') != '':
                parentItem = self.addPipelineItem(categoryItem, data, default)
            else:
                parentItem = categoryItem

            # Presets on second or third level
            if data.get('type', 'preset') == 'pipeline':
                newItem = self.addPipelineItem(categoryItem, data, default)
            else:
                newItem = self.addPresetItem(parentItem, data, default)

            #self.presetList.setCurrentItem(newItem,0)
            QApplication.processEvents()
            return newItem

        except Exception as e:
             QMessageBox.information(self,"Facepager","Error loading preset:"+str(e))
             return None

    def hideDetails(self):
        self.detailName.setText("")
        self.detailModule.setText("")
        self.detailDescription.setText("")
        self.detailOptions.setText("")
        self.detailColumns.setText("")

        self.presetView.hide()
        self.categoryView.hide()

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

            # Create folder
            if not os.path.exists(self.presetFolderDefault):
                os.makedirs(self.presetFolderDefault)

            # Lock file handling
            lockedShas = {}
            newShas = {}
            lock_file_path = os.path.join(self.presetFolderDefault, 'presets.lock')
            if not os.path.exists(lock_file_path):
                open(lock_file_path, 'w').close()
            else:
                with open(lock_file_path, 'r') as file:
                    lockedShas = {line.strip().split(' ', 1)[1]: line.strip().split(' ', 1)[0] for line in
                                     file.readlines()}

            # Create temporary download folder
            tmp = TemporaryDirectory(suffix='FacepagerDefaultPresets')
            try:
                #Download
                files = requests.get(settings.get("presetListUrl")).json()
                files = [f for f in files if f['path'].endswith(tuple(self.presetSuffix))]
                self.progressMax.emit(len(files))

                for fileInfo in files:
                    if self.progress.wasCanceled:
                        raise Exception(f"Downloading default presets was canceled by you.")

                    sha = fileInfo['sha']
                    filename = fileInfo['path']
                    basename = os.path.basename(filename)

                    tmpPath = os.path.join(tmp.name, basename)
                    targetPath = os.path.join(self.presetFolderDefault, basename)

                    if sha not in lockedShas.values() or lockedShas.get(basename) != sha:
                        response = requests.get(settings.get("presetFileUrl") + filename)
                        if response.status_code != 200:
                            raise Exception(f"GitHub is not available (status code {response.status_code})")
                        with open(tmpPath, 'wb') as f:
                            f.write(response.content)
                        newShas[basename] = sha
                    elif os.path.exists(targetPath):
                        shutil.copyfile(targetPath, tmpPath)
                        newShas[basename] = sha

                    self.progressStep.emit()

                #Clear folder
                for filename in os.listdir(self.presetFolderDefault):
                    os.remove(os.path.join(self.presetFolderDefault,filename))

                # Move files from tempfolder
                for filename in os.listdir(tmp.name):
                    shutil.move(os.path.join(tmp.name, filename), self.presetFolderDefault)

                # Update the lock file to reflect actual directory contents
                with open(lock_file_path, 'w') as file:
                    for filename, sha in newShas.items():
                        file.write(f"{sha} {filename}\n")

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

        self.categoryNodes = {}
        self.pipelineNodes = {}
        self.presetList.clear()
        self.presetView.hide()
        self.categoryView.hide()

        selectitem = None

        while not self.presetsDownloaded:
            QApplication.processEvents()

        if os.path.exists(self.presetFolderDefault):
            files = [f for f in os.listdir(self.presetFolderDefault) if f.endswith(tuple(self.presetSuffix))]
            for filename in files:
                newitem = self.addItem(self.presetFolderDefault,filename,True)
                if self.lastSelected is not None and (self.lastSelected == os.path.join(self.presetFolderDefault,filename)):
                    selectitem = newitem

        if os.path.exists(self.presetFolder):
            files = [f for f in os.listdir(self.presetFolder) if f.endswith(tuple(self.presetSuffix))]
            for filename in files:
                newitem = self.addItem(self.presetFolder,filename)
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
            categories.append(data.get('category', 'No category'))

        return categories

    def getPipelines(self):
        pipelines = ['']

        root = self.presetList.invisibleRootItem()
        for i in range(root.childCount()):
            categoryItem = root.child(i)
            for j in range(categoryItem.childCount()):
                pipelineItem = categoryItem.child(j)  # Second-level items within each category
                data = pipelineItem.data(0, Qt.UserRole)
                if data and data.get('type') == 'pipeline':
                    pipelines.append(data.get('name', ''))  # Add the name if the type is 'pipeline'

        return pipelines

    def startPipeline(self, pipelineData):
        if not self.presetList.currentItem():
            return False

        # Get pipeline item
        root_item = self.presetList.currentItem()
        root_data = root_item.data(0, Qt.UserRole)
        if root_data.get('type', '') != 'pipeline':
            return False

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

    def applyPreset(self):
        if not self.presetList.currentItem():
            return False

        data = self.presetList.currentItem().data(0,Qt.UserRole)
        itemType = data.get('type', 'preset')
        if  itemType == 'pipeline':
            self.startPipeline(data)
        elif itemType == 'preset':
            self.mainWindow.apiActions.applySettings(data)

        self.close()

    def addColumns(self):
        if not self.presetList.currentItem():
            return False

        data = self.presetList.currentItem().data(0,Qt.UserRole)
        if data.get('type','preset') == 'preset':
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

        if self.presetList.currentItem().childCount() > 0:
            QMessageBox.information(self, "Facepager", "Delete the child nodes first.")

        if data.get('type', 'preset') == 'category':
            return False

        if (data.get('filename', '') == ''):
            return False

        filePath = os.path.join(self.presetFolder, data.get('filename'))
        if not os.path.exists(filePath):
            return False

        reply = QMessageBox.question(self, 'Delete Preset',"Are you sure to delete the {0} \"{1}\"?".format(data.get('type',''), data.get('name','')), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return False


        os.remove(filePath)
        self.initPresets()

    def editPreset(self,data = None):
        dialog=QDialog(self.mainWindow)

        self.currentData = data if data is not None else {}
        self.currentFilename = self.currentData.get('filename',None)
        itemType = self.currentData.get('type','preset')

        if self.currentFilename is None:
            dialog.setWindowTitle("New {0}".format(itemType))
        else:
            dialog.setWindowTitle("Edit selected {0}".format(itemType))

        layout=QVBoxLayout()
        label=QLabel("<b>Name</b>")
        layout.addWidget(label)
        name=QLineEdit()
        name.setText(self.currentData.get('name',''))
        layout.addWidget(name,0)

        label=QLabel("<b>Category</b>")
        layout.addWidget(label)
        categoryWidget = QComboBox(self)
        categoryWidget.addItems(self.getCategories())
        categoryWidget.setEditable(True)
        categoryWidget.setCurrentText(self.currentData.get('category','No category'))
        layout.addWidget(categoryWidget,0)

        if itemType == 'preset':
            label=QLabel("<b>Pipeline</b>")
            layout.addWidget(label)
            pipelineWidget = QComboBox(self)
            pipelineWidget.addItems(self.getPipelines())
            pipelineWidget.setCurrentIndex(pipelineWidget.findText(self.currentData.get('pipeline', '')))
            layout.addWidget(pipelineWidget,0)
        else:
            pipelineWidget = None

        label=QLabel("<b>Description</b>")
        layout.addWidget(label)
        description=QTextEdit()
        description.setMinimumWidth(500)
        description.acceptRichText=False
        description.setPlainText(self.currentData.get('description',''))
        description.setFocus()
        layout.addWidget(description,1)


        if itemType == 'preset':
            overwriteLayout =QHBoxLayout()
            overwriteCheckbox = QCheckBox(self)
            overwriteCheckbox.setCheckState(Qt.Unchecked)
            overwriteLayout.addWidget(overwriteCheckbox)
            label=QLabel("<b>Overwrite parameters with current settings</b>")
            overwriteLayout.addWidget(label)
            overwriteLayout.addStretch()

            if self.currentFilename is not None:
                layout.addLayout(overwriteLayout)
        else:
            overwriteCheckbox = None

        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        layout.addWidget(buttons,0)
        dialog.setLayout(layout)

        def save():
            if pipelineWidget:
                pipelineName = pipelineWidget.currentText()
                if pipelineName == '':
                    pipelineName = None
            else:
                pipelineName = None

            data_meta = {
                    'name':name.text(),
                    'category':categoryWidget.currentText(),
                    'pipeline': pipelineName,
                    'description':description.toPlainText()
            }
            self.currentData.update(data_meta)

            if itemType == 'preset':
                data_settings = self.mainWindow.apiActions.getPresetOptions()
                if self.currentFilename is None:
                    self.currentData.update(data_settings)

                elif overwriteCheckbox is not None and overwriteCheckbox.isChecked():
                    reply = QMessageBox.question(self, 'Overwrite Preset',"Are you sure to overwrite the selected preset \"{0}\" with the current settings?".format(data.get('name','')), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    if reply != QMessageBox.Yes:
                        dialog.close()
                        self.currentFilename = None
                        return False
                    else:
                        self.currentData.update(data_settings)

            # Sanitize and reorder
            keys = ['name', 'category','type', 'pipeline', 'description', 'module', 'options', 'speed', 'saveheaders','timeout','maxsize','columns']
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
            category = self.currentData.get('category', 'No category')
            self.currentFilename = self.uniqueFilename(category+"-"+name.text())

            with open(os.path.join(self.presetFolder,self.currentFilename), 'w') as outfile:
                json.dump(self.currentData, outfile, indent=2, separators=(',', ': '))

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
        filename = self.editPreset({'type':'preset'})
        if filename is not None:
            newitem = self.addItem(self.presetFolder,filename)
            self.presetList.sortItems(0,Qt.AscendingOrder)
            self.presetList.setCurrentItem(newitem, 0)

    def newPipeline(self):
        filename = self.editPreset({'type':'pipeline'})
        if filename is not None:
            newitem = self.addItem(self.presetFolder,filename)
            self.presetList.sortItems(0,Qt.AscendingOrder)
            self.presetList.setCurrentItem(newitem, 0)

    def overwritePreset(self):
        if not self.presetList.currentItem():
            return False

        item = self.presetList.currentItem()
        data = item.data(0,Qt.UserRole)

        if data.get('default', False):
            QMessageBox.information(self,"Facepager","Cannot edit default presets.")
            return False

        if data.get('type','preset') == 'category':
            return False

        filename = self.editPreset(data)

        if filename is not None:
            item.parent().removeChild(item)
            item = self.addItem(self.presetFolder,filename)

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
