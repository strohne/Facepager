from PySide2.QtCore import *
from PySide2.QtWidgets import *
from database import *
import json

class DataTree(QTreeView):

    nodeSelected = Signal(list)
    logmessage = Signal(str)

    def __init__(self, parent=None):
        super(DataTree, self).__init__(parent)

        #self.setSortingEnabled(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QTreeView.SelectRows)
        self.setUniformRowHeights(True)


    def loadData(self, database):
        self.treemodel = TreeModel(database)
        self.treemodel.logmessage.connect(self.logmessage)
        self.setModel(self.treemodel)

    @Slot()
    def currentChanged(self, current, previous):
        super(DataTree, self).currentChanged(current, previous)
        self.nodeSelected.emit(current) #,self.selectionModel().selectedRows()

    @Slot()
    def selectionChanged(self, selected, deselected):
        super(DataTree, self).selectionChanged(selected, deselected)
        current = self.currentIndex()
        self.nodeSelected.emit(current)  # ,self.selectionModel().selectedRows()

    def selectedCount(self):
        indexes = self.selectionModel().selectedRows()
        return(len(indexes))

    def selectLastRow(self):
        QCoreApplication.processEvents()
        
        model = self.model()
        parent = QModelIndex()
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

    def selectNext(self, filter={}, recursive=False, exact=True, progress=None):
        # Start with selected index or root index
        index = self.selectedIndexes()
        index = index[0] if len(index) else QModelIndex()
        if not recursive:
            filter['level'] = self.model().getLevel(index)

        try:
            options = None
            includeself = False
            index = next(self.getNextOrSelf(index, filter, exact, options, includeself, recursive, progress))
            self.showRow(index)
        except StopIteration:
            pass

    def checkData(self, index, options=None):
        """
        Add last offcut or data node to tree item if resume is in options
        Return False if pagination is finished, otherwise True
        """
        if options is None:
            return True

        if not index.isValid():
            return False

        # Find last offcut or data node
        treeitem = index.internalPointer()
        if options.get('resume', False):
            treeitem.offcut = treeitem.getLastChildData(objecttypes=["data", "offcut"])

            # Dont't fetch if already finished (=has offcut without next cursor)
            if (treeitem.offcut is not None) and (options.get('key_paging') is not None):
                response = getDictValueOrNone(treeitem.offcut, 'response', dump=False)
                cursor = getDictValueOrNone(response, options.get('key_paging'))
                stopvalue = not extractValue(response, options.get('paging_stop'), dump=False, default=True)[1]

                # Dont't fetch if already finished (=offcut without next cursor)
                if (cursor is None) or stopvalue:
                    return False
        else:
            treeitem.offcut = None

        return True

    def checkFilter(self, index, filter=None, exact=True):
        if filter is None:
            return True

        if not index.isValid():
            return False

        treeitem = index.internalPointer()
        for key, value in filter.items():
            if treeitem.data is not None and treeitem.data[key] is not None:
                orlist = value if type(value) is list else [value]
                data = treeitem.data[key]
                exact = exact or not isinstance(data, str)
                if exact and not data in orlist:
                    return False
                elif not exact and not any(v in data for v in orlist):
                    return False

        return True

    def getNextOrSelf(self, index, filter=None, exact=True, options=None, includeself=True, recursive=True, progress=None):
        parent = index.parent()
        row = index.row()
        row_start = row
        row_end = self.model().rowCount(parent)

        # Iterate all nodes on the same level or deeper
        while True:
            if not parent.isValid():
                child = self.model().index(row, 0, parent)
            else:
                child = parent.child(row, 0)

            if progress is not None:
                if not progress(row - row_start,row_end - row_start):
                    break

            if child.isValid():
                includeself = includeself or (row > row_start)
                yield from self.getNextChildOrSelf(child, filter, exact, options, includeself)
            else:
                break
            row += 1

        # Jump to parent node level and select next
        index = parent
        nextindex = QModelIndex()
        while recursive and index.isValid() and not nextindex.isValid():
            parent = index.parent()
            row = index.row()
            nextindex = self.model().index(row+1,0,parent)
            index = parent

        if nextindex.isValid():
            includeself=True
            yield from self.getNextOrSelf(nextindex, filter, exact, options, includeself, recursive, progress)


    def getNextChildOrSelf(self, index, filter=None, exact=True, options=None, includeself=True, persistent=False):
        """
        Yield next node matching the criteria
        """
        level = filter.get('level')

        # if (not selected) and self.selectionModel().isSelected(index):
        #     selected = True

        if includeself and self.checkFilter(index, filter, exact) and self.checkData(index, options):
            if persistent:
                index_persistent = QPersistentModelIndex(index)
                yield (index_persistent)
            else:
                yield (index)

        if (level is None) or (level > self.model().getLevel(index)):
            self.model().fetchMore(index)

            row = 0
            while True:
                if not index.isValid():
                    child = self.model().index(row, 0, index)
                else:
                    child = index.child(row, 0)

                if child.isValid():
                    includeself = True
                    yield from self.getNextChildOrSelf(child, filter, exact, options, includeself, persistent)
                else:
                    break

                row += 1

    def selectedIndexesAndChildren(self, persistent=False, filter={}, selectall = False, options = {}):
        exact = True
        includeself = True

        if selectall:
            yield from self.getNextChildOrSelf(QModelIndex(), filter, exact, options, includeself, persistent)
        else:
            for index in self.selectionModel().selectedRows():
                yield from self.getNextChildOrSelf(index, filter, exact, options, includeself, persistent)


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

    def getLastChildData(self, status="fetched (200)", objecttypes=["offcut"]):
        if not self.id:
            return None

        if not (self.childCountAll() > 0):
            return None

        query = Node.query.filter(Node.parent_id == self.id,Node.querystatus == status,Node.objecttype.in_(objecttypes))
        item = query.order_by(Node.id.desc()).limit(1).first()
        if item is not None:
            item = self.model.getItemData(item)

        return item


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
        if self.parentItem is not None:
            return self.parentItem.childItems.index(self)

        return None


    def appendNodes(self, data, options, headers=None, delaycommit=False):
        """Append nodes after fetching data
        """
        dbnode = Node.query.get(self.id)
        if not dbnode:
            return False

        #filter response
        if options['nodedata'] is None:
            subkey = 0
            nodes = data
            offcut = None
        elif hasDictValue(data,options['nodedata'], piped=True):
            subkey = options['nodedata'].split('|').pop(0).rsplit('.', 1)[0]
            name, nodes = extractValue(data, options['nodedata'], False)
            offcut = filterDictValue(data, options['nodedata'], False, piped=True)
        else:
            subkey = options['nodedata'].split('|').pop(0).rsplit('.', 1)[0]
            nodes = []
            offcut = data

        if not (type(nodes) is list):
            nodes = [nodes]
            fieldsuffix = ''
        else:
            fieldsuffix = '.*'

        newnodes = []

        def appendNode(objecttype, objectid, response, fieldsuffix = ''):
            new = Node(str(objectid), dbnode.id)
            new.objecttype = objecttype
            new.response = response

            new.level = dbnode.level + 1
            new.querystatus = options.get("querystatus", "")
            new.querytime = str(options.get("querytime", ""))
            new.querytype = options.get('querytype', '')

            queryparams = {key : options.get(key,'') for key in  ['nodedata','basepath','resource']}
            queryparams['nodedata'] = queryparams['nodedata'] + fieldsuffix if queryparams['nodedata'] is not None else queryparams['nodedata']
            new.queryparams = queryparams

            newnodes.append(new)


        #empty records
        if len(nodes) == 0:
            appendNode('empty', '', {})

        #extracted nodes
        for n in nodes:
            n = n if isinstance(n, Mapping) else {subkey: n}
            o = options.get('objectid', None)
            o = extractValue(n, o)[1] if o is not None else dbnode.objectid
            appendNode('data', o, n, fieldsuffix)

        #Offcut
        if offcut is not None:
            appendNode('offcut', dbnode.objectid, offcut)

        #Headers
        if options.get('saveheaders',False) and headers is not None:
            appendNode('headers',dbnode.objectid,headers)


        self.model.database.session.add_all(newnodes)
        self._childcountall += len(newnodes)
        dbnode.childcount += len(newnodes)

        self.model.newnodes += len(newnodes)
        self.model.nodecounter += len(newnodes)
        self.model.commitNewNodes(delaycommit)
        # self.model.database.session.commit()
        # self.model.layoutChanged.emit()

    def hasValues(self,filter = {}):
        if self.data is None:
            return False

        for key, value in filter.items():
            orlist = value if type(value) is list else [value]
            if not self.data.get(key) in orlist:
                return False

        return True

    def unpackList(self, key_nodes, key_objectid, delaycommit=False):
        dbnode = Node.query.get(self.id)

        # extract nodes
        name, nodes = extractValue(dbnode.response, key_nodes, dump=False)
        if not (type(nodes) is list):
            nodes = [nodes]

        # add nodes
        #subkey = key_nodes.split("|").pop(0).rsplit('.', 1)[0]
        subkey_name, subkey_key, subkey_pipeline = parseKey(key_nodes)
        subkey = subkey_name if subkey_name is not None else subkey_key.rsplit('.', 1)[0]
        newnodes = []
        for n in nodes:
            objectid = extractValue(n, key_objectid)[1]
            response = n if isinstance(n, Mapping) else {subkey : n}

            new = Node(objectid, dbnode.id)
            new.objecttype = 'unpacked'
            new.response = response
            new.level = dbnode.level + 1
            new.querystatus = dbnode.querystatus
            new.querytime = dbnode.querytime
            new.querytype = dbnode.querytype
            new.queryparams = dbnode.queryparams
            newnodes.append(new)


        self.model.database.session.add_all(newnodes)
        self._childcountall += len(newnodes)
        dbnode.childcount += len(newnodes)

        self.model.newnodes += len(newnodes)
        self.model.nodecounter += len(newnodes)
        self.model.commitNewNodes(delaycommit)

    def __repr__(self):
        return self.id

class TreeModel(QAbstractItemModel):
    logmessage = Signal(str)

    def __init__(self, database, parent=None):
        super(TreeModel, self).__init__(parent)

        self.database = database
        self.customcolumns = []
        self.newnodes = 0
        self.nodecounter = 0

        #Hidden root
        self.rootItem = TreeItem(self)

    def clear(self):
        self.beginResetModel()
        try:
            self.rootItem.clear()
        finally:
            self.endResetModel()

    def setCustomColumns(self,cols):
        self.customcolumns = cols
        self.layoutChanged.emit()

    def deleteNode(self, index, delaycommit=False):
        if (not self.database.connected) or (not index.isValid()) or (index.column() != 0):
            return False

        self.beginRemoveRows(index.parent(), index.row(), index.row())
        item = index.internalPointer()

        Node.query.filter(Node.id == item.id).delete()
        self.newnodes += 1
        self.commitNewNodes(delaycommit)
        item.remove(True)
        self.endRemoveRows()

    def addNodes(self, nodesdata, extended = False):

        try:
            if not self.database.connected:
                return False

            newnodes = []
            for nodedata in nodesdata:
                if isinstance(nodedata, Mapping):
                    objectid = list(nodedata.values())[0]
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
            self.database.session.commit()
            self.rootItem._childcountall += len(nodesdata)

            self.layoutChanged.emit()
        except Exception as e:
            self.logmessage.emit(str(e))

    def commitNewNodes(self, delaycommit=False):
        if (not delaycommit and self.newnodes > 0) or (self.newnodes > 500):
            self.database.session.commit()
            self.newnodes = 0
        if not delaycommit:
            self.layoutChanged.emit()

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            parentNode = self.rootItem
        else:
            parentNode = parent.internalPointer()

        return parentNode.childCount()

    def columnCount(self, parent):
        return 5 + len(self.customcolumns)

    def data(self, index, role):
        if not index.isValid():
            return None

        item = index.internalPointer()

        if (role == Qt.DisplayRole) or (role == Qt.ToolTipRole):
            if index.column() == 0:
                value = item.data.get('objectid','')
            elif index.column() == 1:
                value = item.data.get('objecttype','')
            elif index.column() == 2:
                value = item.data.get('querystatus','')
            elif index.column() == 3:
                value = item.data.get('querytime','')
            elif index.column() == 4:
                value = item.data.get('querytype','')
            else:
                key = self.customcolumns[index.column() - 5]
                value = extractValue(item.data.get('response',''), key)[1]

            if role == Qt.ToolTipRole:
                return wraptip(value)
            else:
                return value

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            # parent is not valid when it is the root node, since the "parent"
            # method returns an empty QModelIndex
            parentNode = self.rootItem
        else:
            parentNode = parent.internalPointer()  # the node

        childItem = parentNode.child(row)

        return self.createIndex(row, column, childItem)

    def parent(self, index):
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
            captions = ['Object ID', 'Object Type', 'Query Status', 'Query Time', 'Query Type'] + extractNames(self.customcolumns)
            return captions[section] if section < len(captions) else ""

        return None

    def getRowHeader(self):
        row = ["id", "parent_id", "level", "object_id", "object_type", "query_status", "query_time", "query_type"]
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

        if not index.isValid():
            item = self.rootItem
        else:
            item = index.internalPointer()

        return item.childCountAll() > 0

    def getLevel(self, index):
        if not index.isValid():
            return -1

        treeitem = index.internalPointer()
        if treeitem.data is not None and treeitem.data['level'] is not None:
            return treeitem.data['level']
        else:
            return 0

    def getItemData(self, item):
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

    def canFetchMore(self, index):
        if not self.database.connected:
            return False

        if not index.isValid():
            item = self.rootItem
        else:
            item = index.internalPointer()

        return item.childCountAll() > item.childCount()

    def fetchMore(self, index):
        if not index.isValid():
            parentItem = self.rootItem
        else:
            parentItem = index.internalPointer()

        if parentItem.childCountAll() == parentItem.childCount():
            return False

        row = parentItem.childCount()
        items = Node.query.filter(Node.parent_id == parentItem.id).offset(row).all()

        self.beginInsertRows(index, row, row + len(items) - 1)

        for item in items:
            itemdata = self.getItemData(item)
            new = TreeItem(self, parentItem, item.id, itemdata)
            new._childcountall = item.childcount
            new._childcountallloaded = True


        self.endInsertRows()
        parentItem.loaded = parentItem.childCountAll() == parentItem.childCount()
