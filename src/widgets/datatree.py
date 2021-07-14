from PySide2.QtCore import *
from PySide2.QtWidgets import *
from database import *
import json
from collections import defaultdict

class DataTree(QTreeView):

    nodeSelected = Signal(QModelIndex)
    logmessage = Signal(str)
    showprogress = Signal(int)
    stepprogress = Signal()
    hideprogress = Signal()

    def __init__(self, parent=None):
        super(DataTree, self).__init__(parent)

        #self.setSortingEnabled(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QTreeView.SelectRows)
        self.setUniformRowHeights(True)


    def loadData(self, database):
        self.treemodel = TreeModel(database)
        self.treemodel.logmessage.connect(self.logmessage)
        self.treemodel.showprogress.connect(self.showprogress.emit)
        self.treemodel.hideprogress.connect(self.hideprogress.emit)
        self.treemodel.stepprogress.connect(self.stepprogress.emit)
        self.setModel(self.treemodel)

    @Slot()
    def currentChanged(self, current, previous):
        super(DataTree, self).currentChanged(current, previous)
        self.nodeSelected.emit(current)

    @Slot()
    def selectionChanged(self, selected, deselected):
        super(DataTree, self).selectionChanged(selected, deselected)
        current = self.currentIndex()
        self.nodeSelected.emit(current)

    def selectedCount(self):
        indexes = self.selectionModel().selectedRows()
        return(len(indexes))

    def selectLastRow(self):
        QCoreApplication.processEvents()
        
        model = self.model()
        parent = QModelIndex()
        model.fetchMore(parent)
        row = model.rowCount(parent)-1
         
        index = model.index(row, 0, parent)
        self.showRow(index)

    def showRow(self,index):
        if not index.isValid():
            return False

        self.scrollTo(index)
        self.selectionModel().select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
        self.selectionModel().setCurrentIndex(index, QItemSelectionModel.Rows)

    def noneOrAllSelected(self):
        indexes = self.selectionModel().selectedRows()

        if len(indexes) == 0:
            return True
        else:
            model = self.model()
            indexes = [idx for idx in indexes if idx.parent() == self.rootIndex()]
            return len(indexes) == model.rootItem.childCount()

    def selectNext(self, conditions={}, progress=None):
        # Start with selected index or root index
        index = self.selectedIndexes()
        if not len(index):
            startindex = self.model().index(0, 0, QModelIndex())
            conditions['includeself'] = True
        else:
            startindex = index[0]
            conditions['includeself'] = False

        try:
            # todo: turnaround, conditions['until'] = startindex
            index = next(self.model().getNextOrSelf(startindex, conditions, progress))
            self.showRow(index)
        except StopIteration:
            pass

    def selectedIndexesAndChildren(self, conditions={}, progress=None):
        """
        Yield the next selected index or its children
        Default conditions are: persistent = False, filter = {}, selectall = False, options = {},
                                exact = True, includeself = True
        """
        if conditions.get('selectall'):
            yield from self.model().getNextChildOrSelf(QModelIndex(), conditions, progress)
        else:
            indexes = self.selectionModel().selectedIndexes()
            indexes = [index for index in indexes if index.column()==0]

            row_end = len(indexes)
            row=1
            for index in indexes:
                row+=1
                if progress is not None:
                    if not progress(row, row_end):
                        break
                yield from self.model().getNextChildOrSelf(index, conditions, progress)


class TreeItem(object):
    def __init__(self, model=None, parent=None, id=None, data=None):
        self.model = model

        self.id = id
        self.data = data

        self.parentItem = parent
        self.childItems = []

        self.loaded = False
        self._childcountallloaded = False
        self._childcountall = 0
        self._row = None

        if parent is not None:
            parent.appendChild(self)

    def appendChild(self, item, persistent=False):
        item.parentItem = self
        self.childItems.append(item)

        item._row = len(self.childItems)-1
        if persistent:
            self._childcountall += 1

    def removeChild(self, position):
        if position < 0 or position > len(self.childItems):
            return False
        child = self.childItems.pop(position)
        child.parentItem = None

        return True

    def child(self, row):
        return self.childItems[row]

    def parent(self):
        return self.parentItem

    def setParent(self, new_parent):
        self.parentItem.childItems.remove(self)
        self.parentItem = new_parent
        new_parent.childItems.append(self)

    def clear(self):
        self.childItems = []
        self.loaded = False
        self._childcountallloaded = False

    def remove(self, persistent=False):
        self.parentItem.removeChild(self, persistent)

    def removeChild(self, child, persistent=False):
        if child in self.childItems:
            rowidx = child.row()
            #del self.childItems[rowidx]
            self.childItems.remove(child)

            #Update row indexes
            for row in range(rowidx, len(self.childItems) - 1):
                self.childItems[row]._row = row

            if persistent:
                self._childcountall -= 1
                dbnode = self.dbnode()
                if dbnode:
                    dbnode.childcount -= 1

    def childCount(self):
        """Return number of loaded children"""
        return len(self.childItems)

    def childCountAll(self):
        """Return number of children in database"""
        if not self._childcountallloaded:
            self._childcountall = Node.query.filter(Node.parent_id == self.id).count()
            self._childcountallloaded = True
        return self._childcountall

    def parentid(self):
        return self.parentItem.id if self.parentItem else None

    def dbnode(self):
        if self.id:
            return Node.query.get(self.id)
        else:
            return None

    def level(self):
        if self.data is None:
            return 0
        else:
            return self.data['level']

    def row(self):
        return self._row
        # if self.parentItem is not None:
        #     return self.parentItem.childItems.index(self)

        return None


    def appendNodes(self, data, options, delaycommit=False):
        """Append nodes after fetching data
        """
        dbnode = Node.query.get(self.id)
        if not dbnode:
            return False

        newnodes = []

        def appendNode(objecttype, objectid, response, extractedkey=''):
            new = Node(str(objectid), dbnode.id)
            new.objecttype = objecttype
            new.response = response

            new.level = dbnode.level + 1
            new.querystatus = options.get("querystatus", "")
            new.querytime = str(options.get("querytime", ""))
            new.querytype = options.get('querytype', '')

            queryparams = {key : options.get(key,'') for key in  ['nodedata','basepath','resource']}
            queryparams['nodedata'] = extractedkey
            new.queryparams = queryparams

            newnodes.append(new)

        #empty records
        if data['empty'] is not None:
            appendNode('empty', dbnode.objectid, data['empty'])

        #extracted nodes
        for k, n in data['nodes']:
            # Extract Object ID or use parent id if no key present
            o = options.get('objectid')
            if o is not None:
                o = extractValue(n, o, default=None)[1]
            if o is None:
                o = dbnode.objectid

            objecttype = options.get('objecttype', 'data')
            appendNode(objecttype, o, n, k)

        #offcut
        if data['offcut'] is not None:
            appendNode('offcut', dbnode.objectid, data['offcut'])

        #headers
        if data['headers'] is not None:
            appendNode('headers', dbnode.objectid, data['headers'])

        self.model.database.session.add_all(newnodes)
        self._childcountall += len(newnodes)
        dbnode.childcount += len(newnodes)

        self.model.newnodes += len(newnodes)
        self.model.nodecounter += len(newnodes)
        self.model.commitNewNodes(delaycommit)
        # self.model.database.session.commit()
        # self.model.layoutChanged.emit()
        return (len(data['nodes']))

    def hasValues(self,filter = {}):
        if self.data is None:
            return False

        for key, value in filter.items():
            orlist = value if type(value) is list else [value]
            if not self.data.get(key) in orlist:
                return False

        return True

    def unpackList(self, key_nodes, key_objectid, delaycommit=False):
        options={
            'nodedata':key_nodes,
            'objectid':key_objectid,
            'offcut': False,
            'empty': True,
            'objecttype': 'unpacked',
            'querystatus': self.data.get("querystatus", ""),
            'querytime': self.data.get("querytime", ""),
            'querytype': self.data.get('querytype', '')
            #'queryparams' : self.data.get('queryparams',{})
        }

        data = sliceData(self.data.get("response", {}), None, options)
        self.appendNodes(data, options, delaycommit=delaycommit)

    def copyNode(self, delaycommit=False):
        objectid = self.data.get("objectid")
        self.model.addSeedNodes([objectid],delaycommit=delaycommit)


    def __repr__(self):
        return self.id

class TreeModel(QAbstractItemModel):
    logmessage = Signal(str)
    showprogress = Signal(int)
    hideprogress = Signal()
    stepprogress = Signal()


    def __init__(self, database, parent=None):
        super(TreeModel, self).__init__(parent)

        self.database = database
        self.customcolumns = []
        self.newnodes = 0
        self.nodecounter = 0

        # Cache for prefetching data
        self.prefetching = False
        self.cache = defaultdict(defaultdict)

        #Hidden root
        self.rootItem = TreeItem(self)

    def clear(self):
        self.cache.clear()
        self.beginResetModel()
        try:
            self.rootItem.clear()
        finally:
            self.endResetModel()

    def setCustomColumns(self,cols):
        self.customcolumns = cols
        self.layoutChanged.emit()

    def deleteNode(self, index, delaycommit=False):
        if (not self.database.connected) or\
                (not index.isValid()) or\
                (index.column() != 0):
            return False

        self.beginRemoveRows(index.parent(), index.row(), index.row())
        item = index.internalPointer()

        Node.query.filter(Node.id == item.id).delete()
        self.newnodes += 1
        self.commitNewNodes(delaycommit)
        item.remove(True)
        self.endRemoveRows()

    def addSeedNodes(self, nodesdata, extended=False, progress=None, delaycommit=False):
        """
        Add seed nodes
        """

        try:
            if not self.database.connected:
                return False

            newnodes = []
            for nodedata in nodesdata:
                if progress is not None:
                    if not progress():
                        return False

                if isinstance(nodedata, Mapping):
                    objectid = nodedata.pop(list(nodedata.keys())[0])
                    response = nodedata

                elif extended:
                    nodedata = nodedata.split('|',1)
                    objectid = nodedata[0]
                    try:
                        response = json.loads(nodedata[1]) if len(nodedata) > 1 else None
                    except Exception as e:
                        response = {'error':str(e)}

                else:
                    objectid = nodedata
                    response = None

                new = Node(objectid)
                if isinstance(response,  Mapping):
                    new.response = response

                newnodes.append(new)

            self.database.session.add_all(newnodes)
            self.rootItem._childcountall += len(newnodes)
            self.rootItem.loaded = False

            self.newnodes += len(newnodes)
            self.commitNewNodes(delaycommit)
            #self.database.session.commit()
            #self.layoutChanged.emit()

        except Exception as e:
            self.logmessage.emit(str(e))

    def commitNewNodes(self, delaycommit=False):
        if (not delaycommit and self.newnodes > 0) or (self.newnodes > 500):
            self.database.session.commit()
            self.newnodes = 0
        if not delaycommit:
            self.layoutChanged.emit()

    def rowCount(self, parent=QModelIndex()):
        parentNode = self.getItemFromIndex(parent)
        return parentNode.childCount()

    def columnCount(self, parent):
        return 6 + len(self.customcolumns)

    def data(self, index, role):
        if not index.isValid():
            return None

        item = index.internalPointer()

        if (role == Qt.DisplayRole) or (role == Qt.ToolTipRole):
            custom_len = len(self.customcolumns)
            default_len = 6

            # Default columns
            if index.column() == 0:
                value = item.data.get('objectid','')
            elif index.column() == 1:
                value = item.data.get('objecttype','')
            elif index.column() == 2:
                value = getDictValue(item.data.get('queryparams',''), 'nodedata')
            elif index.column() == 3:
                value = item.data.get('querystatus','')
            elif index.column() == 4:
                value = item.data.get('querytime','')
            elif index.column() == 5:
                value = item.data.get('querytype','')

            # Custom columns
            else:
                key = self.customcolumns[index.column() - default_len]
                value = extractValue(item.data.get('response',''), key)[1]

            if role == Qt.ToolTipRole:
                return wraptip(value)
            else:
                return value

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            return self.createIndex(row, column, self.rootItem.childItems[row])

        parentNode = parent.internalPointer()
        childItem = parentNode.childItems[row]

        return self.createIndex(row, column, childItem)

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        node = index.internalPointer()
        parentNode = node.parent()

        if parentNode == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentNode.row(), 0, parentNode)

    # def flags(self, index):
    #
    #     # Original, inherited flags:
    #     original_flags = super(TreeModel, self).flags(index)
    #
    #     return (original_flags | Qt.ItemIsEnabled
    #             | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled
    #             | Qt.ItemIsDropEnabled)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            captions = ['Object ID','Object Type', 'Object Key', 'Query Status', 'Query Time', 'Query Type']
            captions += extractNames(self.customcolumns)
            return captions[section] if section < len(captions) else ""

        return None

    def getRowHeader(self):
        row = ["id", "parent_id", "level", "object_id", "object_type", "object_key", "query_status", "query_time", "query_type"]
        columns = extractNames(self.customcolumns)
        for key in columns:
            row.append(key)
        return row

    def getRowData(self, index):
        node = index.internalPointer()
        row = [node.id,
               node.parentItem.id,
               node.data['level'],
               node.data['objectid'],
               node.data['objecttype'],
               getDictValue(node.data['queryparams'],'nodedata'),
               node.data['querystatus'],
               node.data['querytime'],
               node.data['querytype']
              ]
        for key in self.customcolumns:
            row.append(extractValue(node.data['response'],key)[1])
        return row

    def hasChildren(self, index):
        if not self.database.connected:
            return False

        item = self.getItemFromIndex(index)
        return item.childCountAll() > 0

    def getLevel(self, index):
        if not index.isValid():
            return -1

        treeitem = index.internalPointer()
        if treeitem.data is not None and treeitem.data['level'] is not None:
            return treeitem.data['level']
        else:
            return 0

    def getItemDataFromRecord(self, item):
        """Creates dict for model items (itemdata) from database row (item)"""
        itemdata = {'level': item.level,
                    'childcount': item.childcount,
                    'objectid': item.objectid,
                    'objecttype': item.objecttype,
                    'querystatus': item.querystatus,
                    'querytime': item.querytime,
                    'querytype': item.querytype,
                    'queryparams': item.queryparams,
                    'response': item.response}
        return itemdata

    def getItemFromIndex(self, index):
        """
          Get TreeItem for QModelIndex
          Note: index is not valid when it is the root node, return rootItem
          Note: parent method of top level indexes returns an empty QModelIndex)
        """
        if not index.isValid():
            return self.rootItem
        else:
            return index.internalPointer()

    # def getIndexFromId(self, id, startindex=None, loaddata=True):
    #     """
    #     Get QModelIndex from id of TreeItem / record
    #     (only for loaded indexes)
    #     """
    #
    #     # Start search with first node
    #     if startindex is None:
    #         startindex = self.index(0, 0, QModelIndex())
    #
    #     for index in self.getNextOrSelf(startindex, {'loaddata': loaddata}):
    #         item = self.getItemFromIndex(index)
    #         if item.id == id:
    #             return index
    #
    #     return QModelIndex()

    def appendRecords(self, parent, records):
        if not len(records):
            return False

        parentItem = self.getItemFromIndex(parent)
        if parentItem == self.rootItem:
            self.showprogress.emit(len(records))
        try:
            lastRow = parentItem.childCount()

            self.beginInsertRows(parent, lastRow, lastRow + len(records) - 1)

            for record in records:
                itemdata = self.getItemDataFromRecord(record)
                new = TreeItem(self, parentItem, record.id, itemdata)
                new._childcountall = record.childcount
                new._childcountallloaded = True

                if parentItem == self.rootItem:
                    self.stepprogress.emit()

            self.endInsertRows()
            parentItem.loaded = parentItem.childCountAll() <= parentItem.childCount()
        finally:
            if parentItem == self.rootItem:
                self.hideprogress.emit()

    def getLastChildData(self, index, filter=None):
        self.fetchMore(index)
        row = self.rowCount(index)-1

        # Iterate all nodes backwards
        while row >= 0:
            child = index.child(row, 0)
            if self.checkFilter(child, filter):
                item = self.getItemFromIndex(child)
                return item.data

            row -= 1
        return None

    def canFetchMore(self, index):
        if not self.database.connected:
            return False

        item = self.getItemFromIndex(index)
        return item.childCountAll() > item.childCount()

    def fetchMore(self, index):
        parentItem = self.getItemFromIndex(index)

        # From cache (append, fetch, clear in one operation)
        #self.prefetch(index)

        # Remaining
        if parentItem.childCountAll() > parentItem.childCount():
            row = parentItem.childCount()
            items = Node.query.filter(Node.parent_id == parentItem.id).offset(row).all()
            self.appendRecords(index, items)

    def prefetch(self, parentIndex, chunk=1000):
        # Append from cache if possible
        self.appendFromCache(parentIndex)

        # Get next chunks
        parentItem = self.getItemFromIndex(parentIndex)
        while parentItem.childCountAll() > parentItem.childCount():
            row = parentItem.childCount()
            if parentItem.id is None:
                records = Node.query.filter(Node.parent_id == parentItem.id).offset(row).all()
            else:
                missing = parentItem.childCountAll() - row
                nextchunk = missing if missing > chunk else chunk
                records = Node.query.filter(Node.parent_id >= parentItem.id).offset(row).limit(nextchunk).all()

            # Add to cache, grouped by parent_id and id to avoid duplicates
            for record in records:
                self.cache[record.parent_id][record.id] = record

            # Append new items from cache
            self.appendFromCache(parentIndex)

    def appendFromCache(self, parentIndex):
        parentItem = self.getItemFromIndex(parentIndex)
        if not parentItem.id in self.cache:
            return False

        # Get and remove slice from cache
        recordsDict = self.cache[parentItem.id]
        del self.cache[parentItem.id]
        if parentItem.loaded:
            return False

        # Filter out items after last child to avoid duplicates
        # (records are ordered by ID)
        lastRow = parentItem.childCount()
        if lastRow > 0:
            lastChild = parentItem.childItems[-1]
            lastId = lastChild.id
            recordsDict = {id: record for id, record in recordsDict.items() if id > lastId}

        # Add remainder
        recordsList = recordsDict.values()
        self.appendRecords(parentIndex, recordsList)


    def checkData(self, index, options=None):
        """
        Add last offcut or data node to tree item if resume is in options
        Return False if pagination is finished, otherwise True
        """
        if options is None:
            return True

        if not index.isValid():
            return False

        treeitem = index.internalPointer()

        # Check if empty
        if options.get('emptyonly', False):
            return treeitem.childCountAll() == 0

        # Find last offcut or data node
        elif options.get('resume', False):
            filter = {
                'querystatus': "fetched (200)",
                'objecttype': ["data", "offcut", "empty"],
                'querytype': options.get('querytype', '')
            }
            treeitem.lastdata = self.getLastChildData(index, filter)

            # Dont't fetch if already finished (=has offcut without next cursor)
            if (treeitem.lastdata is not None):
                response = getDictValueOrNone(treeitem.lastdata, 'response', dump=False)
                cursor = getDictValueOrNone(response, options.get('key_paging'))
                stopvalue = not extractValue(response, options.get('paging_stop'), dump=False, default=True)[1]

                # Dont't fetch if already finished (=offcut without next cursor)
                if (cursor is None) or stopvalue:
                    return False
        else:
            treeitem.lastdata = None

        return True

    def checkFilter(self, index, filter=None, exact=True):
        if filter is None:
            return True

        if not index.isValid():
            return False

        treeitem = index.internalPointer()
        for key, value in filter.items():
            inverse = key[0] == '!'
            key = key[1:] if key[0] == '!' else key

            if treeitem.data is not None and treeitem.data[key] is not None:
                orlist = value if type(value) is list else [value]
                data = treeitem.data[key]
                try:
                    data = str(data) if isinstance(data, Mapping) else data

                    # Exact match
                    if exact or not isinstance(data, str):
                        if (inverse and data in orlist):
                            return False
                        elif (not inverse and not data in orlist):
                            return False
                        
                    # Partial string match
                    elif not any(v in data for v in orlist):
                        return False


                except:
                    return False

        return True

    def getNextOrSelf(self, index, conditions={}, progress=None):
        """
        Yield next node matching the criteria
        Default conditions are: filter = None, exact = True, options = None, includeself = True, recursive = True
        """

        parent = index.parent()
        row = index.row()
        row_start = row
        row_end = self.rowCount(parent)-1
        level = self.getLevel(index)

        recursive = conditions.get('recursive',True)
        if not recursive:
            conditions['filter'] = conditions.get('filter', {})
            conditions['filter']['level'] = level

        # Iterate all nodes on the same level or deeper
        while True:
            if not parent.isValid():
                child = self.index(row, 0, parent)
            else:
                child = parent.child(row, 0)

            if progress is not None:
                if not progress(row - row_start,row_end - row_start + 1, level):
                    break

            if child.isValid():
                conditions['includeself'] = conditions.get('includeself',True) or (row > row_start)
                conditions['persistent'] = False
                yield from self.getNextChildOrSelf(child, conditions, progress)
            else:
                break
            row += 1

        # Jump to parent node level and select next
        index = parent
        nextindex = QModelIndex()
        while recursive and index.isValid() and not nextindex.isValid():
            parent = index.parent()
            row = index.row()
            nextindex = self.index(row+1,0,parent)
            index = parent

        if nextindex.isValid():
            conditions['includeself']=True
            yield from self.getNextOrSelf(nextindex, conditions, progress)


    def getNextChildOrSelf(self, index, conditions={}, progress=None):
        """
        Yield next child node matching the criteria

        Default conditions are: filter=None, exact=True, options=None, includeself=True,
                                        persistent=False
        """
        # Self
        includeself = conditions.get('includeself', True)
        filter = conditions.get('filter')
        options = conditions.get('options')
        exact = conditions.get('exact', True)

        if includeself and self.checkFilter(index, filter, exact) and self.checkData(index, options):
            if conditions.get('persistent'):
                index_persistent = QPersistentModelIndex(index)
                yield (index_persistent)
            else:
                yield (index)

        # Children
        maxlevel = filter.get('level') if filter is not None else None
        level = self.getLevel(index)

        if (maxlevel is None) or (maxlevel > level):
            self.fetchMore(index)

            if progress is not None:
                row_end = self.rowCount(index) - 1

            row = 0
            while True:
                if progress is not None:
                    if not progress(row, row_end+1, level+1):
                        break

                if not index.isValid():
                    child = self.index(row, 0, index)
                else:
                    child = index.child(row, 0)

                if child.isValid():
                    conditions['includeself'] = True
                    yield from self.getNextChildOrSelf(child, conditions, progress)
                else:
                    break
                row += 1
