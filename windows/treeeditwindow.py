#    Copyright (C) 2004-2006 Jeremy S. Sanders
#    Email: Jeremy Sanders <jeremy@jeremysanders.net>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
###############################################################################

# $Id$

"""Edit the document using a tree and properties.
"""

import os

import veusz.qtall as qt4

import veusz.widgets as widgets
import veusz.utils as utils
import veusz.document as document

import action

class WidgetTreeModel(qt4.QAbstractItemModel):
    """A model representing the widget tree structure.
    """

    def __init__(self, document, parent=None):
        """Initialise using document."""
        
        qt4.QAbstractItemModel.__init__(self, parent)

        self.document = document

        self.connect( self.document, qt4.SIGNAL("sigModified"),
                      self.slotDocumentModified )
        self.connect( self.document, qt4.SIGNAL("sigWiped"),
                      self.slotDocumentModified )

    def slotDocumentModified(self):
        """The document has been changed."""
        self.emit( qt4.SIGNAL('layoutChanged()') )

    def columnCount(self, parent):
        """Return number of columns of data."""
        return 2

    def data(self, index, role):
        """Return data for the index given."""

        # why do we get passed invalid indicies? :-)
        if not index.isValid():
            return qt4.QVariant()

        column = index.column()
        obj = index.internalPointer()

        if role == qt4.Qt.DisplayRole:
            # return text for columns
            if column == 0:
                return qt4.QVariant(obj.name)
            elif column == 1:
                return qt4.QVariant(obj.typename)
        elif role == qt4.Qt.DecorationRole:
            # return icon for first column
            if column == 0:
                return qt4.QVariant(action.getIcon('button_%s.png' %
                                                   obj.typename))
        elif role == qt4.Qt.ToolTipRole:
            # provide tool tip showing description
            if obj.userdescription:
                return qt4.QVariant(obj.userdescription)

        # return nothing
        return qt4.QVariant()

    def setData(self, index, value, role):
        """User renames object. This renames the widget."""
        
        widget = index.internalPointer()
        name = unicode(value.toString())

        # check symbols in name
        if not utils.validateWidgetName(name):
            return False
        # check name not already used
        if widget.parent.hasChild(name):
            return False

        self.document.applyOperation(
            document.OperationWidgetRename(widget, name))

        self.emit( qt4.SIGNAL('dataChanged(const QModelIndex &, const QModelIndex &)'), index, index )
        return True
            
    def flags(self, index):
        """What we can do with the item."""
        
        if not index.isValid():
            return qt4.Qt.ItemIsEnabled

        flags = qt4.Qt.ItemIsEnabled | qt4.Qt.ItemIsSelectable
        if index.internalPointer() is not self.document.basewidget and index.column() == 0:
            # allow items other than root to be edited
            flags |= qt4.Qt.ItemIsEditable
        return flags

    def headerData(self, section, orientation, role):
        """Return the header of the tree."""
        
        if orientation == qt4.Qt.Horizontal and role == qt4.Qt.DisplayRole:
            val = ['Name', 'Type', 'Detail'][section]
            return qt4.QVariant(val)

        return qt4.QVariant()

    def _getChildren(self, parent):
        """Get a list of children for the parent given (None selects root)."""

        if parent is None:
            return [self.document.basewidget]
        else:
            return parent.children

    def index(self, row, column, parent):
        """Construct an index for a child of parent."""

        if not parent.isValid():
            parentobj = None
        else:
            parentobj = parent.internalPointer()

        children = self._getChildren(parentobj)

        c = children[row]
        return self.createIndex(row, column, c)

    def getWidgetIndex(self, widget):
        """Returns index for widget specified."""

        # walk index tree back to widget from root
        widgetlist = []
        w = widget
        while w is not None:
            widgetlist.append(w)
            w = w.parent

        # now iteratively look up indices
        parent = qt4.QModelIndex()
        while widgetlist:
            w = widgetlist.pop()
            row = self._getChildren(w.parent).index(w)
            parent = self.index(row, 0, parent)

        return parent
    
    def parent(self, index):
        """Find the parent of the index given."""

        if not index.isValid():
            return qt4.QModelIndex()

        thisobj = index.internalPointer()
        parentobj = thisobj.parent

        if parentobj is None:
            return qt4.QModelIndex()
        else:
            # lookup parent in grandparent's children
            grandparentchildren = self._getChildren(parentobj.parent)
            parentrow = grandparentchildren.index(parentobj)

            return self.createIndex(parentrow, 0, parentobj)

    def rowCount(self, parent):
        """Return number of rows of children."""
        
        if not parent.isValid():
            parentobj = None
        else:
            parentobj = parent.internalPointer()

        children = self._getChildren(parentobj)
        return len(children)

    def getSettings(self, index):
        """Return the settings for the index selected."""

        obj = index.internalPointer()
        return obj.settings

    def getWidget(self, index):
        """Get associated widget for index selected."""
        obj = index.internalPointer()

        return obj

class PropertyList(qt4.QWidget):
    """Edit the widget properties using a set of controls."""

    def __init__(self, document, showsubsettings=True, *args):
        qt4.QWidget.__init__(self, *args)
        self.document = document
        self.showsubsettings = showsubsettings

        self.layout = qt4.QGridLayout(self)

        self.layout.setSpacing( self.layout.spacing()/2 )
        self.layout.setMargin(4)
        
        self.children = []

    def updateProperties(self, settings):
        """Update the list of controls with new ones for the settings."""

        # delete all child widgets
        self.setUpdatesEnabled(False)
        while len(self.children) > 0:
            self.children.pop().deleteLater()

        if settings is None:
            self.setUpdatesEnabled(True)
            return

        row = 0
        # FIXME: add actions

        self.layout.setEnabled(False)
        # add subsettings if necessary
        if settings.getSettingsList() and self.showsubsettings:
            tabbed = TabbedFormatting(self.document, settings, self)
            self.layout.addWidget(tabbed, row, 1, 1, 2)
            row += 1
            self.children.append(tabbed)

        for setn in settings.getSettingList():
            lab = SettingLabelButton(self.document, setn, self)
            self.layout.addWidget(lab, row, 0)
            self.children.append(lab)

            cntrl = setn.makeControl(self)
            self.connect(cntrl, qt4.SIGNAL('settingChanged'),
                         self.slotSettingChanged)
            self.layout.addWidget(cntrl, row, 1)
            self.children.append(cntrl)

            row += 1
        self.setUpdatesEnabled(True)
        self.layout.setEnabled(True)
 
    def slotSettingChanged(self, widget, setting, val):
        """Called when a setting is changed by the user.
        
        This updates the setting to the value using an operation so that
        it can be undone.
        """
        
        self.document.applyOperation(document.OperationSettingSet(setting, val))
        
class TabbedFormatting(qt4.QTabWidget):
    """Class to have tabbed set of settings."""

    def __init__(self, document, settings, *args):
        qt4.QTabWidget.__init__(self, *args)

        if settings is None:
            return

        # add tab for each subsettings
        for subset in settings.getSettingsList():

            # create tab
            tab = qt4.QWidget()
            layout = qt4.QVBoxLayout()
            layout.setMargin(2)
            tab.setLayout(layout)

            # create scrollable area
            scroll = qt4.QScrollArea(tab)
            layout.addWidget(scroll)
            scroll.setWidgetResizable(True)

            # create list of properties
            plist = PropertyList(document)
            plist.updateProperties(subset)
            scroll.setWidget(plist)
            plist.show()

            # add tab to widget
            if hasattr(subset, 'pixmap'):
                icon = action.getIcon('settings_%s.png' % subset.pixmap)
                indx = self.addTab(tab, icon, '')
                self.setTabToolTip(indx, subset.name)
            else:
                self.addTab(tab, subset.name)

class FormatDock(qt4.QDockWidget):
    """A window for formatting the current widget.
    Provides tabbed formatting properties
    """

    def __init__(self, document, treeedit, *args):
        qt4.QDockWidget.__init__(self, *args)
        self.setWindowTitle("Formatting - Veusz")
        self.setObjectName("veuszformattingdock")

        self.document = document
        self.tabwidget = None

        # update our view when the tree edit window selection changes
        self.connect(treeedit, qt4.SIGNAL('widgetSelected'),
                     self.selectWidget)

    def selectWidget(self, widget):
        """Created tabbed widget for formatting for each subsettings."""

        # delete old tabwidget
        if self.tabwidget:
            self.tabwidget.deleteLater()
            self.tabwidget = None

        # create new tabbed widget showing formatting
        settings = None
        if widget is not None:
            settings = widget.settings

        self.tabwidget = TabbedFormatting(self.document, settings, self)
        self.setWidget(self.tabwidget)

class PropertiesDock(qt4.QDockWidget):
    """A window for editing properties for widgets."""

    def __init__(self, document, treeedit, *args):
        qt4.QDockWidget.__init__(self, *args)
        self.setWindowTitle("Properties - Veusz")
        self.setObjectName("veuszpropertiesdock")

        self.document = document

        # update our view when the tree edit window selection changes
        self.connect(treeedit, qt4.SIGNAL('widgetSelected'),
                     self.selectWidget)

        # construct scrollable area
        self.scroll = qt4.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.setWidget(self.scroll)

        # construct properties list in scrollable area
        self.proplist = PropertyList(document, showsubsettings=False)
        self.scroll.setWidget(self.proplist)

    def selectWidget(self, widget):
        """Update properties when selected widget changes."""

        settings = None
        if widget is not None:
            settings = widget.settings
        self.proplist.updateProperties(settings)

class TreeEditDock(qt4.QDockWidget):
    """A window for editing the document as a tree."""

    # mime type when widgets are stored on the clipboard
    widgetmime = 'text/x-vnd.veusz-clipboard'

    def __init__(self, document, parent):
        qt4.QDockWidget.__init__(self, parent)
        self.parent = parent
        self.setWindowTitle("Editing - Veusz")
        self.setObjectName("veuszeditingwindow")

        # construct tree
        self.document = document
        self.treemodel = WidgetTreeModel(document)
        self.treeview = qt4.QTreeView()
        self.treeview.setModel(self.treemodel)

        # receive change in selection
        self.connect(self.treeview.selectionModel(),
                     qt4.SIGNAL('selectionChanged(const QItemSelection &, const QItemSelection &)'),
                     self.slotTreeItemSelected)

        # set tree as main widget
        self.setWidget(self.treeview)

        # toolbar to create widgets, etc
        self.toolbar = qt4.QToolBar("Editing toolbar - Veusz",
                                    parent)
        self.toolbar.setObjectName("veuszeditingtoolbar")
        self.toolbar.setOrientation(qt4.Qt.Vertical)
        parent.addToolBar(qt4.Qt.LeftToolBarArea, self.toolbar)
        self._constructToolbarMenu()

        # this sets various things up
        self.selectWidget(document.basewidget)

        # update paste button when clipboard changes
        self.connect(qt4.QApplication.clipboard(),
                     qt4.SIGNAL('dataChanged()'),
                     self.updatePasteButton)

    def slotTreeItemSelected(self, current, previous):
        """New item selected in tree.

        This updates the list of properties
        """
        
        indexes = current.indexes()

        if len(indexes) > 1:
            index = indexes[0]
            self.selwidget = self.treemodel.getWidget(index)
            settings = self.treemodel.getSettings(index)
        else:
            self.selwidget = None
            settings = None

        self._enableCorrectButtons()
        self._checkPageChange()

        self.emit( qt4.SIGNAL('widgetSelected'), self.selwidget )

    def _checkPageChange(self):
        """Check to see whether page has changed."""

        w = self.selwidget
        while w is not None and not isinstance(w, widgets.Page):
            w = w.parent

        if w is not None:
            # have page, so check what number we are in basewidget children
            try:
                i = self.document.basewidget.children.index(w)
                self.emit(qt4.SIGNAL("sigPageChanged"), i)
            except ValueError:
                pass

    def _enableCorrectButtons(self):
        """Make sure the create graph buttons are correctly enabled."""

        selw = self.selwidget

        # check whether each button can have this widget
        # (or a parent) as parent

        menu = self.parent.menus['insert']
        for wc, action in self.addslots.iteritems():
            w = selw
            while w is not None and not wc.willAllowParent(w):
                w = w.parent

            self.addactions['add%s' % wc.typename].setEnabled(w is not None)

        # certain actions shouldn't allow root to be deleted
        isnotroot = not isinstance(selw, widgets.Root)

        for i in ('cut', 'copy', 'delete', 'moveup', 'movedown'):
            self.editactions[i].setEnabled(isnotroot)

        if isnotroot:
            # cut and copy aren't currently possible on a non-widget
            cancopy = selw is not None
            self.editactions['cut'].setEnabled(cancopy)
            self.editactions['copy'].setEnabled(cancopy)
        self.updatePasteButton()

    def _getWidgetOrder(self):
        """Return a list of the widgets, most important first.
        """

        # get list of allowed classes, sorted by type name
        wcl = [(i.typename, i)
               for i in document.thefactory.listWidgetClasses()
               if i.allowusercreation]
        wcl.sort()

        # build up a list of pairs for topological sort
        pairs = []
        for name, wc in wcl:
            for pwc in wc.allowedparenttypes:
                pairs.append( (pwc, wc) )

        # do topological sort
        sorted = utils.topsort(pairs)

        return sorted

    def _constructToolbarMenu(self):
        """Add items to edit/add graph toolbar and menu."""

        self.toolbar.setIconSize( qt4.QSize(16, 16) )

        actions = []
        self.addslots = {}
        for wc in self._getWidgetOrder():
            name = wc.typename
            if wc.allowusercreation:

                slot = utils.BoundCaller(self.slotMakeWidgetButton, wc)
                self.addslots[wc] = slot

                val = ( 'add%s' % name, wc.description,
                        'Add %s' % name, 'insert',
                        slot,
                        'button_%s.png' % name,
                        True, '')
                actions.append(val)
        self.addactions = action.populateMenuToolbars(actions, self.toolbar,
                                                      self.parent.menus)
        self.toolbar.addSeparator()

        # make buttons and menu items for the various item editing ops
        moveup = utils.BoundCaller(self.slotWidgetMove, -1)
        movedown = utils.BoundCaller(self.slotWidgetMove, 1)
        self.editslots = [moveup, movedown]

        edititems = (
            ('cut', 'Cut the selected item', 'Cu&t', 'edit',
             self.slotWidgetCut, 'stock-cut.png', True, 'Ctrl+X'),
            ('copy', 'Copy the selected item', '&Copy', 'edit',
             self.slotWidgetCopy, 'stock-copy.png', True, 'Ctrl+C'),
            ('paste', 'Paste item from the clipboard', '&Paste', 'edit',
             self.slotWidgetPaste, 'stock-paste.png', True, 'Ctrl+V'),
            ('moveup', 'Move the selected item up', 'Move &up', 'edit',
             moveup, 'stock-go-up.png',
             True, ''),
            ('movedown', 'Move the selected item down', 'Move d&own', 'edit',
             movedown, 'stock-go-down.png',
             True, ''),
            ('delete', 'Remove the selected item', '&Delete', 'edit',
             self.slotWidgetDelete, 'stock-delete.png', True, '')
            )
        self.editactions = action.populateMenuToolbars(edititems, self.toolbar,
                                                       self.parent.menus)

    def slotMakeWidgetButton(self, wc):
        """User clicks button to make widget."""
        self.makeWidget(wc.typename)

    def makeWidget(self, widgettype, autoadd=True, name=None):
        """Called when an add widget button is clicked.
        widgettype is the type of widget
        autoadd specifies whether to add default children
        if name is set this name is used if possible (ie no other children have it)
        """

        # if no widget selected, bomb out
        if self.selwidget is None:
            return
        parent = self.getSuitableParent(widgettype)

        assert parent is not None

        if name in parent.childnames:
            name = None
        
        # make the new widget and update the document
        w = self.document.applyOperation( document.OperationWidgetAdd(parent, widgettype, autoadd=autoadd,
                                                                      name=name) )

        # select the widget
        self.selectWidget(w)

    def getSuitableParent(self, widgettype, initialParent = None):
        """Find the nearest relevant parent for the widgettype given."""

        # get the widget to act as the parent
        if not initialParent:
            parent = self.selwidget
        else:
            parent  = initialParent
        
        # find the parent to add the child to, we go up the tree looking
        # for possible parents
        wc = document.thefactory.getWidgetClass(widgettype)
        while parent is not None and not wc.willAllowParent(parent):
            parent = parent.parent

        return parent

    def slotWidgetCut(self):
        """Cut the selected widget"""
        self.slotWidgetCopy()
        self.slotWidgetDelete()

    def slotWidgetCopy(self):
        """Copy selected widget to the clipboard."""

        mimedata = self._makeMimeData(self.selwidget)
        if mimedata:
            clipboard = qt4.QApplication.clipboard()
            clipboard.setMimeData(mimedata)
            #clipboard.setText(mimedata)

    def _makeMimeData(self, widget):
        """Make a QMimeData object representing the subtree with the
        current selection at the root"""

        if widget:
            mimedata = qt4.QMimeData()
            text = str('\n'.join((widget.typename,
                                  widget.name,
                                  widget.getSaveText())))
            self.mimedata = qt4.QByteArray(text)
            mimedata.setData('text/plain', self.mimedata)
            #mimedata.setText(text)
            return mimedata
            #return text
        else:
            return None

    def getClipboardData(self):
        """Return the clipboard data if it is in the correct format."""

        mimedata = qt4.QApplication.clipboard().mimeData()
        if self.widgetmime in mimedata.formats():
            data = unicode(mimedata.data(self.widgetmime)).split('\n')
            return data
        else:
            return None

    def updatePasteButton(self):
        """Is the data on the clipboard a valid paste at the currently
        selected widget? If so, enable paste button"""

        data = self.getClipboardData()
        show = False
        if data:
            # The first line of the clipboard data is the widget type
            widgettype = data[0]
            # Check if we can paste into the current widget or a parent
            if self.getSuitableParent(widgettype, self.selwidget):
                show = True

        self.editactions['paste'].setEnabled(show)

    def slotWidgetPaste(self, a):
        """Paste something from the clipboard"""

        data = self.getClipboardData()
        if data:
            # The first line of the clipboard data is the widget type
            widgettype = data[0]
            # The second is the original name
            widgetname = data[1]

            # make the document enter batch mode
            # This is so that the user can undo this in one step
            op = document.OperationMultiple([], descr='paste')
            self.document.applyOperation(op)
            self.document.batchHistory(op)
            
            # Add the first widget being pasted
            self.makeWidget(widgettype, autoadd=False, name=widgetname)
            
            interpreter = self.parent.interpreter
        
            # Select the current widget in the interpreter
            tmpCurrentwidget = interpreter.interface.currentwidget
            interpreter.interface.currentwidget = self.selwidget

            # Use the command interface to create the subwidgets
            for command in data[2:]:
                interpreter.run(command)
                
            # stop the history batching
            self.document.batchHistory(None)
                
            # reset the interpreter widget
            interpreter.interface.currentwidget = tmpCurrentwidget
            
    def slotWidgetDelete(self):
        """Delete the widget selected."""

        # no item selected, so leave
        w = self.selwidget
        if w is None:
            return

        # get list of widgets in order
        widgetlist = []
        self.document.basewidget.buildFlatWidgetList(widgetlist)
        
        widgetnum = widgetlist.index(w)
        assert widgetnum >= 0

        # delete selected widget
        self.document.applyOperation( document.OperationWidgetDelete(w) )

        # rebuild list
        widgetlist = []
        self.document.basewidget.buildFlatWidgetList(widgetlist)

        # find next to select
        if widgetnum < len(widgetlist):
            nextwidget = widgetlist[widgetnum]
        else:
            nextwidget = self.document.basewidget

        # select the next widget
        self.selectWidget(nextwidget)

    def selectWidget(self, widget):
        """Select the associated listviewitem for the widget w in the
        listview."""

        index = self.treemodel.getWidgetIndex(widget)
        self.treeview.scrollTo(index)
        self.treeview.setCurrentIndex(index)

    def slotWidgetMove(self, direction):
        """Move the selected widget up/down in the hierarchy.

        a is the action (unused)
        direction is -1 for 'up' and +1 for 'down'
        """

        # widget to move
        w = self.selwidget
        
        # actually move the widget
        self.document.applyOperation(
            document.OperationWidgetMove(w, direction) )

        # rehilight moved widget
        self.selectWidget(w)

class SettingLabelButton(qt4.QPushButton):
    """A label next to each setting in the form of a button."""

    def __init__(self, document, setting, parent):
        """Initialise botton, passing document, setting, and parent widget."""
        
        qt4.QPushButton.__init__(self, setting.name, parent)

        self.document = document
        self.setting = setting

        self.setToolTip(setting.descr)
        self.connect(self, qt4.SIGNAL('clicked()'), self.settingMenu)
        self.setSizePolicy(qt4.QSizePolicy.Maximum, qt4.QSizePolicy.Maximum)

    def settingMenu(self):
        """Pop up menu for each setting."""

        # forces settings to be updated
        self.parentWidget().setFocus()
        # get it back straight away
        self.setFocus()

        # get widget, with its type and name
        widget = self.setting.parent
        while not isinstance(widget, widgets.Widget):
            widget = widget.parent
        self._clickwidget = widget

        wtype = widget.typename
        name = widget.name

        popup = qt4.QMenu(self)
        popup.addAction('Reset to default', self.actionResetDefault)
        popup.addSeparator()
        popup.addAction('Copy to "%s" widgets' % wtype,
                        self.actionCopyTypedWidgets)
        popup.addAction('Copy to "%s" siblings' % wtype,
                        self.actionCopyTypedSiblings)
        popup.addAction('Copy to "%s" widgets called "%s"' % (wtype, name),
                        self.actionCopyTypedNamedWidgets)
        popup.addSeparator()
        popup.addAction('Make default for "%s" widgets' % wtype,
                        self.actionDefaultTyped)
        popup.addAction('Make default for "%s" widgets called "%s"' %
                        (wtype, name),
                        self.actionDefaultTypedNamed)
        popup.addAction('Forget this default setting',
                        self.actionDefaultForget)
        popup.exec_(qt4.QCursor.pos())

    def actionResetDefault(self):
        self.document.applyOperation( document.OperationSettingSet(self.setting, self.setting.default) )

    def actionCopyTypedWidgets(self):
        self.document.applyOperation( document.OperationSettingPropagate(self.setting) )

    def actionCopyTypedSiblings(self):
        self.document.applyOperation( document.OperationSettingPropagate(self.setting, root=self._clickwidget.parent, maxlevels=1) )

    def actionCopyTypedNamedWidgets(self):
        self.document.applyOperation( document.OperationSettingPropagate(self.setting, widgetname=self._clickwidget.name) )

    def actionDefaultTyped(self):
        self.setting.setAsDefault(False)

    def actionDefaultTypedNamed(self):
        self.setting.setAsDefault(True)

    def actionDefaultForget(self):
        self.setting.removeDefault()
    
            
##############################################################

# define this so stuff runs below (all needs updating for qt4)
XListViewItem = qt4.QObject
XHBox = qt4.QWidget
XTable = qt4.QWidget
XDockWindow = qt4.QWidget

class _WidgetItem(XListViewItem):
    """Item for displaying in the TreeEditWindow."""

    def __init__(self, widget, qtparent):
        """Widget is the widget to show the settings for."""
        
        XListViewItem.__init__(self, qtparent)
        self.setRenameEnabled(0, True)

        self.index = 0
        self.widget = widget
        self.settings = widget.settings

        self.setPixmap(0, action.getPixmap('button_%s.png' % widget.typename) )
        
        self.recursiveAddPrefs(0, self.settings, self)

    def getAssociatedWidget(self):
        """Return the widget associated with this item."""
        return self.widget
        
    def recursiveAddPrefs(self, no, settings, parent):
        """Recursively add preference subsettings."""
        for s in settings.getSettingsList():
            i = _PrefItem(s, no, parent)
            no += 1
            no = self.recursiveAddPrefs(no, s, i)
            
        return no
            
    def setText(self, col, text):
        """Update name of widget if rename is called."""

        # update name of widget
        if col == 0:
            try:
                self.widget.document.applyOperation(
                    document.OperationWidgetRename(self.widget, unicode(text)) )
            except ValueError:
                # if the rename failed
                text = self.widget.name

        XListViewItem.setText(self, col, text)

    def rename(self):
        """Rename the listviewitem."""
        self.startRename(0)

    def compare(self, i, col, ascending):
        """Always sort according to the index value."""

        a = [-1, 1][ascending]
            
        if self.index < i.index:
            return -1*a
        elif self.index > i.index:
            return 1*a
        else:
            return 0

    def text(self, column):
        """Get the text in a particular column."""
        if column == 0:
            return self.widget.name
        elif column == 1:
            return self.widget.typename
        elif column == 2:
            return self.widget.userdescription
        return ''

class _PrefItem(XListViewItem):
    """Item for displaying a preferences-set in TreeEditWindow."""
    def __init__(self, settings, number, parent):
        """settings is the settings class to work for
        parent is the parent ListViewItem (of type _WidgetItem)
        """

        XListViewItem.__init__(self, parent)

        self.settings = settings
        self.parent = parent
        self.widget = None
        self.setText(0, settings.name)
        self.setText(1, 'setting')
        self.index = number

        if hasattr(settings, 'pixmap'):
            self.setPixmap(0, action.getPixmap('settings_%s.png' %
                                               settings.pixmap) )
        
    def compare(self, i, col, ascending):
        """Always sort according to the index value."""

        a = [-1, 1][ascending]
           
        if self.index < i.index:
            return -1*a
        elif self.index > i.index:
            return 1*a
        else:
            return 0

    def getAssociatedWidget(self):
        """Get widget associated with this item."""
        self.parent.getAssociatedWidget()

class _NewPropertyLabel(XHBox):
    """A widget for displaying the label for a setting."""

    def __init__(self, setting, parent):

        XHBox.__init__(self, parent)
        self.setting = setting

        self.menubutton = qt4.QPushButton(setting.name, self)
        self.menubutton.setFlat(True)
        self.connect(self.menubutton, qt4.SIGNAL('clicked()'),
                     self.slotContextMenu)
        
        tooltext = "<strong>%s</strong> - %s" % (setting.name,
                                                 setting.descr)
        qt4.QToolTip.add(self.menubutton, tooltext)

        self.linkbutton = qt4.QPushButton(action.getIconSet('link.png'), '', self)
        self.linkbutton.setMaximumWidth(self.linkbutton.height())
        self.linkbutton.setFlat(True)

        self.connect(self.linkbutton, qt4.SIGNAL('clicked()'),
                     self.buttonClicked)

        setting.setOnModified(self.slotOnModified)
        # show linkbutton if appropriate, update tooltip
        self.slotOnModified(True)
        
    def slotOnModified(self, mod):
        """Alter reference button if setting is modified."""
        
        isref = self.setting.isReference()
        if isref:
            ref = self.setting.getReference()
            qt4.QToolTip.add(self.linkbutton, "Linked to %s" % ref.value)
        self.linkbutton.setShown(isref)

    def getWidget(self):
        """Get associated Veusz widget."""
        widget = self.setting.parent
        while not isinstance(widget, widgets.Widget):
            widget = widget.parent
        return widget

    def slotContextMenu(self):
        """Pop up the context menu."""

        # forces settings to be updated
        self.parentWidget().setFocus()
        # get it back straight away
        self.menubutton.setFocus()

        widget = self.getWidget()
        wtype = widget.typename
        name = widget.name
        
        # construct the popup menu
        popup = qt4.QPopupMenu(self)

        popup.insertItem('Reset to default', 0)
        popup.insertSeparator()
        popup.insertItem('Copy to "%s" widgets' % wtype, 100)
        popup.insertItem('Copy to "%s" siblings' % wtype, 101)
        popup.insertItem('Copy to "%s" widgets called "%s"' %
                         (wtype, name), 102)
        popup.insertSeparator()
        popup.insertItem('Make default for "%s" widgets' % wtype, 200)
        popup.insertItem('Make default for "%s" widgets called "%s"' %
                         (wtype, name), 201)
        popup.insertItem('Forget this default setting', 202)

        #pos = self.menubutton.mapToGlobal(self.menubutton.pos())
        ret = popup.exec_loop( qt4.QCursor.pos() )

        # convert values above to functions
        doc = widget.document
        setn = self.setting
        fnmap = {
            0: (lambda: doc.applyOperation( document.OperationSettingSet(setn, setn.default) )),
            100: (lambda: doc.applyOperation( document.OperationSettingPropagate(setn) )),
            101: (lambda: doc.applyOperation( document.OperationSettingPropagate(setn, root=widget.parent, maxlevels=1) )),
            102: (lambda: doc.applyOperation( document.OperationSettingPropagate(setn, widgetname=name) )),
            
            200: (lambda: setn.setAsDefault(False)),
            201: (lambda: setn.setAsDefault(True)),
            202: setn.removeDefault
            }

        # call the function if item was selected
        if ret >= 0:
            fnmap[ret]()

    def buttonClicked(self):
        """Create a popup menu when the button is clicked."""
        popup = qt4.QPopupMenu(self)

        popup.insertItem('Unlink setting', 100)
        popup.insertItem('Edit linked setting', 101)
        
        ret = popup.exec_loop( qt4.QCursor.pos() )

        setn = self.setting
        widget = self.getWidget()
        doc = widget.document
        if ret == 100:
            # update setting with own value to get rid of reference
            doc.applyOperation( document.OperationSettingSet(setn, setn.get()) )

class _PropertyLabelLabel(qt4.QLabel):
    """A widget for displaying the actual label in the property label."""

    def __init__(self, setting, text, parent):
        """Initialise widget showing text

        setting is the appropriate setting."""
        
        qt4.QLabel.__init__(self, text, parent)
        self.bgcolor = self.paletteBackgroundColor()
        self.setFocusPolicy(qt4.QWidget.StrongFocus)
        self.setMargin(1)

        self.setting = setting
        self.inmenu = False
        self.inmouse = False
        self.infocus = False
        self.parent = parent
        
    def _setBg(self):
        """Set the background of the widget according to its state."""

        # darken widget according to num (100 is normal state)
        num = 100
        if self.inmenu:
            num += 20
        else:
            if self.inmouse:
                num += 10
            if self.infocus:
                num += 10
        
        self.setPaletteBackgroundColor(self.bgcolor.dark(num))

    def enterEvent(self, event):
        """When the mouse enters the widget."""
        qt4.QLabel.enterEvent(self, event)
        self.inmouse = True
        self._setBg()

    def leaveEvent(self, event):
        """When the mouse leaves the widget."""
        qt4.QLabel.leaveEvent(self, event)
        self.inmouse = False
        self._setBg()

    def focusInEvent(self, event):
        """When widget gets focus."""
        qt4.QLabel.focusInEvent(self, event)
        self.infocus = True
        self._setBg()

    def focusOutEvent(self, event):
        """When widget loses focus."""
        qt4.QLabel.focusOutEvent(self, event)
        self.infocus = False
        self._setBg()

    def keyPressEvent(self, event):
        """Use cursor keys to move focus."""

        key = event.key()
        # move up two as in a 2 column grid
        if key == qt4.Qt.Key_Up:
            self.focusNextPrevChild(False)
            self.focusNextPrevChild(False)
        elif key == qt4.Qt.Key_Down:
            self.focusNextPrevChild(True)
            self.focusNextPrevChild(True)
        elif key == qt4.Qt.Key_Left:
            self.focusNextPrevChild(False)
        elif key == qt4.Qt.Key_Right:
            self.focusNextPrevChild(True)
        else:
            event.ignore()

    def contextMenuEvent(self, event):
        """Pop up the context menu."""

        # for labels which don't correspond to settings
        if self.setting is None:
            event.ignore()
            return

        # forces settings to be updated
        self.parentWidget().setFocus()
        # get it back straight away
        self.setFocus()

        # get widget, with its type and name
        widget = self.setting.parent
        while not isinstance(widget, widgets.Widget):
            widget = widget.parent

        wtype = widget.typename
        name = widget.name

        popup = qt4.QMenu(self)
        popup.addAction('Reset to default', self.actionResetDefault)
        popup.addSeparator()
        popup.addAction('Copy to "%s" widgets' % wtype,
                        self.actionCopyTypedWidgets)
        popup.addAction('Copy to "%s" siblings' % wtype,
                        self.actionCopyTypedSiblings)
        popup.addAction('Copy to "%s" widgets called "%s"' % (wtype, name),
                        self.actionCopyTypedNamedWidgets)
        popup.addSeparator()
        popup.addAction('Make default for "%s" widgets' % wtype,
                        self.actionDefaultTyped)
        popup.addAction('Make default for "%s" widgets called "%s"' %
                        (wtype, name),
                        self.actionDefaultTypedNamed)
        popup.addAction('Forget this default setting',
                        self.actionDefaultForget)
        popup.exec_()

    def actionCopyTypedWidgets(self):
        
        ret = popup.exec_loop( event.globalPos() )

        # convert values above to functions
        doc = widget.document
        setn = self.setting
        fnmap = {
            0: (lambda: self.parent.control.emit( qt4.SIGNAL('settingChanged'),
                                                  (self.parent.control, setn, setn.default) )),
            100: (lambda: doc.applyOperation( document.OperationSettingPropagate(setn) )),
            101: (lambda: doc.applyOperation( document.OperationSettingPropagate(setn, root=widget.parent, maxlevels=1) )),
            102: (lambda: doc.applyOperation( document.OperationSettingPropagate(setn, widgetname=name) )),
            
            200: (lambda: setn.setAsDefault(False)),
            201: (lambda: setn.setAsDefault(True)),
            202: setn.removeDefault
            }

        # call the function if item was selected
        if ret >= 0:
            fnmap[ret]()

        # return widget to previous colour
        self.inmenu = False
        self._setBg()
            
class _PropertyLabel(XHBox):
    """A label which produces the veusz setting context menu.

    This label handles mouse move and focus events. Both of these
    shade the widget darker, giving the user information that the widget
    has focus, and a context menu.
    """

    def __init__(self, setting, text, parent):
        """Initialise the label for the given setting."""

        XHBox.__init__(self, parent)
        self.setMargin(0)
        self.setting = setting
        self.control = None

        self.label = _PropertyLabelLabel(setting, text, self)
        self.label.setSizePolicy( qt4.QSizePolicy(qt4.QSizePolicy.Minimum,
                                                  qt4.QSizePolicy.Fixed) )
        
class _WidgetListView(qt4.QListView):
    """A list view for the widgets

    It emits contextMenu signals, and allows widgets to be selected
    """

    def contextMenuEvent(self, event):
        """Emit a context menu signal."""
        self.emit( qt4.SIGNAL('contextMenu'), (event.globalPos(),) )

    def selectWidget(self, widget):
        """Find the widget in the list and select it."""

        # check each item in the list to see whether it corresponds
        # to the widget
        iter = XListViewItemIterator(self)

        found = None
        while True:
            item = iter.current()
            if item is None:
                break
            if item.widget == widget:
                found = item
                break
            iter += 1

        if found:
            self.ensureItemVisible(found)
            self.setSelected(found, True)

class _PropTable(XTable):
    """The table which shows the properties of the selected widget."""

    def __init__(self, parent):
        """Initialise the table."""
        qttable.QTable.__init__(self, parent)
        self.setFocusPolicy(qt4.QWidget.NoFocus)
        self.setNumCols(2)
        self.setTopMargin(0)
        self.setLeftMargin(0)
        self.setShowGrid(False)
        self.setColumnStretchable(1, True)
        self.setSelectionMode(qttable.QTable.NoSelection)

    def keyPressEvent(self, event):
        """This method is necessary as the table steals keyboard input
        even if it cannot have focus."""
        fw = self.focusWidget()
        if fw != self:
            try:
                fw.keyPressEvent(event)
            except RuntimeError:
                # doesn't work for controls which aren't Python based
                event.ignore()
        else:
            event.ignore()

    def keyReleaseEvent(self, event):
        """This method is necessary as the table steals keyboard input
        even if it cannot have focus."""
        fw = self.focusWidget()
        if fw != self:
            try:
                fw.keyReleaseEvent(event)
            except RuntimeError:
                # doesn't work for controls which aren't Python based
                event.ignore()
        else:
            event.ignore()

class TreeEditWindow(XDockWindow):
    """A graph editing window with tree display."""

    # mime type when widgets are stored on the clipboard
    widgetmime = 'text/x-vnd.veusz-clipboard'

    def __init__(self, thedocument, parent):
        XDockWindow.__init__(self, parent)
        self.setResizeEnabled( True )
        self.setCaption("Editing - Veusz")

        self.parent = parent
        self.document = thedocument
        self.connect( self.document, qt4.SIGNAL("sigModified"),
                      self.slotDocumentModified )
        self.connect( self.document, qt4.SIGNAL("sigWiped"),
                      self.slotDocumentWiped )

        # make toolbar in parent to have the add graph/edit graph buttons
        self.edittool = qt4.QToolBar(parent, "treetoolbar")
        self.edittool.setLabel("Editing toolbar - Veusz")
        parent.moveDockWindow(self.edittool, qt4.Qt.DockLeft, True, 0)

        self._constructToolbarMenu()

        # window uses vbox for arrangement
        totvbox = qt4.QVBox(self)
        self.setWidget(totvbox)

        # put widgets in a movable splitter
        split = qt4.QSplitter(totvbox)
        split.setOrientation(qt4.QSplitter.Vertical)

        # first widget is a listview
        vbox = qt4.QVBox(split)
        l = qt4.QLabel("Items", vbox)
        l.setMargin(2)

        lv = self.listview = _WidgetListView(vbox)
        l.setBuddy(lv)
        lv.setSorting(-1)
        lv.setRootIsDecorated(True)
        self.connect( lv, qt4.SIGNAL("selectionChanged(QListViewItem*)"),
                      self.slotItemSelected )
        self.connect( lv, qt4.SIGNAL('contextMenu'),
                      self.slotListContextMenu )

        # we use a hidden column to get the sort order correct
        lv.addColumn( "Name" )
        lv.addColumn( "Type" )
        lv.addColumn( "Detail" )
        lv.setColumnWidthMode(2, qt4.QListView.Manual)
        lv.setSorting(0)
        lv.setTreeStepSize(10)

        # add root widget to view
        self.rootitem = _WidgetItem( self.document.basewidget, lv )

        # add a scrollable view for the preferences
        # children get added to prefview
        vbox = qt4.QVBox(split)
        self.proplabel = qt4.QLabel("&Properties", vbox)
        self.proplabel.setMargin(2)
        self.proplabel.setBuddy(self)
        self.proptab = _PropTable(vbox)

        self.prefchilds = []

        # select the root item
        self.listview.setSelected(self.rootitem, True)

    def sizeHint(self):
        """Returns recommended size of dialog."""
        return qt4.QSize(250, 500)

    def _constructToolbarMenu(self):
        """Add items to edit/add graph toolbar and menu."""

        # make buttons to add each of the widget types
        self.createGraphActions = {}

        insertmenu = self.parent.menus['insert']

        for wc in self._getWidgetOrder():
            name = wc.typename
            if wc.allowusercreation:
                a = action.Action(self,
                                  (lambda w:
                                   (lambda a: self.slotMakeWidgetButton(w)))
                                  (name),
                                  iconfilename = 'button_%s.png' % name,
                                  menutext = 'Add %s' % name,
                                  statusbartext = wc.description,
                                  tooltiptext = wc.description)

                a.addTo(self.edittool)
                a.addTo(insertmenu)
                self.createGraphActions[wc] = a

        self.edittool.addSeparator()

        # make buttons and menu items for the various item editing ops
        self.editactions = {}
        editmenu = self.parent.menus['edit']

        self.contextpopup = qt4.QPopupMenu(self)

        for name, icon, tooltip, menutext, accel, slot in (
            ('cut', 'stock-cut.png', 'Cut the selected item',
             '&Cut', 'Ctrl+X',
             self.slotWidgetCut),
            ('copy', 'stock-copy.png', 'Copy the selected item',
             '&Copy', 'Ctrl+C',
             self.slotWidgetCopy),
            ('paste', 'stock-paste.png', 'Paste from the clipboard',
             '&Paste','Ctrl+V',
             self.slotWidgetPaste),
            ('moveup', 'stock-go-up.png', 'Move the selected item up',
             'Move &up','',
             lambda a: self.slotWidgetMove(a, -1) ),
            ('movedown', 'stock-go-down.png', 'Move the selected item down',
             'Move &down','',
             lambda a: self.slotWidgetMove(a, 1) ),
            ('delete', 'stock-delete.png', 'Remove the selected item',
             '&Delete','',
             self.slotWidgetDelete),
            ('rename', 'icon-rename.png', 'Rename the selected item',
             '&Rename','',
             self.slotWidgetRename)
            ):

            a = action.Action(self, slot,
                              iconfilename = icon,
                              menutext = menutext,
                              statusbartext = tooltip,
                              tooltiptext = tooltip,
                              accel=accel)
            a.addTo(self.edittool)
            a.addTo(self.contextpopup)
            a.addTo(editmenu)
            self.editactions[name] = a

    def _getWidgetOrder(self):
        """Return a list of the widgets, most important first.
        """

        # get list of allowed classes
        wcl = [(i.typename, i)
               for i in document.thefactory.listWidgetClasses()
               if i.allowusercreation]
        wcl.sort()

        # build up a list of pairs for topological sort
        pairs = []
        for name, wc in wcl:
            for pwc in wc.allowedparenttypes:
                pairs.append( (pwc, wc) )

        # do topological sort
        sorted = utils.topsort(pairs)

        return sorted

    def slotDocumentModified(self, ismodified):
        """Called when the document has been modified."""
 
        if ismodified:
            self.updateContents()

    def _updateBranch(self, root):
        """Recursively update items on branch."""

        # build dictionary of items
        items = {}
        i = root.firstChild()
        while i is not None:
            w = i.widget
            if w is not None:
                items[w] = i
            i = i.nextSibling()

        childdict = {}
        # assign indicies to each one
        index = 10000
        newitem = False
        for c in root.widget.children:
            childdict[c] = True
            if c in items:
                items[c].index = index
            else:
                items[c] = _WidgetItem(c, root)
                items[c].index = index
                newitem = True
            self._updateBranch(items[c])
            index += 1

        # delete items not in child list
        for i in items.itervalues():
            if i.widget not in childdict:
                root.takeItem(i)

        # have to re-sort children to ensure ordering is correct here
        root.sort()

        # open the branch if we've added/changed the children
        if newitem:
            self.listview.setOpen(root, True)

    def slotDocumentWiped(self):
        """Called when there is a new document."""

        self.listview.clear()
        self.rootitem = _WidgetItem( self.document.basewidget,
                                     self.listview )
        self.listview.setSelected(self.rootitem, True)
        self.updateContents()

    def updateContents(self):
        """Make the window reflect the document."""

        self._updateBranch(self.rootitem)
        sel = self.listview.selectedItem()
        if sel is not None:
            self.listview.ensureItemVisible(sel)

        self.listview.triggerUpdate()

    def enableCorrectButtons(self, item):
        """Make sure the create graph buttons are correctly enabled."""
        selw = item.getAssociatedWidget()

        # check whether each button can have this widget
        # (or a parent) as parent
        for wc, action in self.createGraphActions.items():
            w = selw
            while w is not None and not wc.willAllowParent(w):
                w = w.parent
            action.enable( w is not None )

        # certain actions shouldn't allow root to be deleted
        isnotroot = not isinstance(selw, widgets.Root)
        
        self.editactions['cut'].enable(isnotroot)
        self.editactions['copy'].enable(isnotroot)
        self.editactions['delete'].enable(isnotroot)
        self.editactions['rename'].enable(isnotroot)
        self.editactions['moveup'].enable(isnotroot)
        self.editactions['movedown'].enable(isnotroot)

        if isnotroot:
            # cut and copy aren't currently possible on a non-widget
            cancopy = item.widget is not None
            self.editactions['cut'].enable(cancopy)
            self.editactions['copy'].enable(cancopy)
       
    def _makeSettingControl(self, row, setn):
        """Construct widget for settting on the row given."""
        tooltext = "<strong>%s</strong> - %s" % (setn.name,
                                                 setn.descr)
        
        view = self.proptab.viewport()
        l = _NewPropertyLabel(setn, view)
        self.proptab.setCellWidget(row, 0, l)
        self.prefchilds.append(l)

        c = setn.makeControl(view)
        c.veusz_rownumber = row
        self.connect(c, qt4.SIGNAL('settingChanged'), self.slotSettingChanged)
        self.proptab.setCellWidget(row, 1, c)
        qt4.QToolTip.add(c, tooltext)
        self.prefchilds.append(c)

        l.control = c
        
        self.proptab.adjustRow(row)
    
    def slotItemSelected(self, item):
        """Called when an item is selected in the listview."""

        # enable or disable the create graph buttons
        self.enableCorrectButtons(item)

        self.itemselected = item
        self.updatePasteButton()

        # delete the current widgets in the preferences list
        while len(self.prefchilds) > 0:
            i = self.prefchilds.pop()

            # need line below or occasionally get random error
            # "QToolTip.maybeTip() is abstract and must be overridden"
            #qt4.QToolTip.remove(i)

            i.deleteLater()

        # calculate number of rows
        rows = len(item.settings.getSettingList())
        w = item.widget
        if w is not None:
            rows += len(w.actions)
        self.proptab.setNumRows(rows)

        row = 0
        view = self.proptab.viewport()
        # add action for widget
        if w is not None:
            for name in w.actions:
                l = _PropertyLabel(None, name, view)
                self.proptab.setCellWidget(row, 0, l)
                self.prefchilds.append(l)

                b = qt4.QPushButton(w.actiondescr[name], view)
                b.veusz_action = w.actionfuncs[name]
                self.proptab.setCellWidget(row, 1, b)
                self.prefchilds.append(b)
                
                self.connect( b, qt4.SIGNAL('clicked()'),
                              self.slotActionClicked )
                row += 1

        # make new widgets for the preferences
        for setn in item.settings.getSettingList():
            self._makeSettingControl(row, setn)
            row += 1

        # make properties keyboard shortcut point to first item
        if len(self.prefchilds) > 0:
            self.proplabel.setBuddy(self.prefchilds[0])
        else:
            self.proplabel.setBuddy(self)
            
        # Change the page to the selected widget
        w = item.widget
        if w is None:
            w = item.parent.widget

        # repeat until we're at the root widget or we hit a page
        while w is not None and not isinstance(w, widgets.Page):
            w = w.parent

        if w is not None:
            # we have a page
            count = 0
            children = self.document.basewidget.children
            for c in children:
                if c == w:
                    break
                count += 1

            if count < len(children):
                self.emit( qt4.SIGNAL("sigPageChanged"), (count,) )
            
    def slotSettingChanged(self, widget, setting, val):
        """Called when a setting is changed by the user.
        
        This updates the setting to the value using an operation so that
        it can be undone.
        """
        
        self.document.applyOperation(document.OperationSettingSet(setting, val))
            
    def slotMakeWidgetButton(self, widgettype):
        """Called when an add widget button is clicked.
        widgettype is the type of widget
        """

        self.makeWidget(widgettype)

    def makeWidget(self, widgettype, autoadd=True, name=None):
        """Called when an add widget button is clicked.
        widgettype is the type of widget
        autoadd specifies whether to add default children
        if name is set this name is used if possible (ie no other children have it)
        """

        # if no widget selected, bomb out
        if self.itemselected is None:
            return
        parent = self.getSuitableParent(widgettype)

        assert parent is not None

        if name in parent.childnames:
            name = None
        
        # make the new widget and update the document
        w = self.document.applyOperation( document.OperationWidgetAdd(parent, widgettype, autoadd=autoadd,
                                                                      name=name) )

        # select the widget
        self.selectWidget(w)

    def getSuitableParent(self, widgettype, initialParent = None):
        """Find the nearest relevant parent for the widgettype given."""

        # get the widget to act as the parent
        if not initialParent:
            parent = self.itemselected.widget
        else:
            parent  = initialParent
        
        if parent is None:
            parent = self.itemselected.parent.widget
            assert parent is not None

        # find the parent to add the child to, we go up the tree looking
        # for possible parents
        wc = document.thefactory.getWidgetClass(widgettype)
        while parent is not None and not wc.willAllowParent(parent):
            parent = parent.parent

        return parent

    def slotActionClicked(self):
        """Called when an action button is clicked."""

        # get the button clicked/activated
        button = self.sender()

        # set focus to button to make sure other widgets lose
        # focus and update their settings
        button.setFocus()

        # run action in console
        action = button.veusz_action
        console = self.parent.console
        console.runFunction( action )

    def getClipboardData(self):
        """Return veusz clipboard data or False if no data is avaliable
        The first line of the returned data is a widget type, the
        remaining lines are commands to customise the widget and add children
        """

        clipboard = qt4.qApp.clipboard()
        cbSource = clipboard.data(clipboard.Clipboard)
        if not cbSource.provides(self.widgetmime):
            # Bail if the clipboard doesn't provide the data type we want
            return False
        
        data = unicode(cbSource.encodedData(self.widgetmime))
        data = data.split('\n')
        return data

    def _makeDragObject(self, widget):
        """Make a QDrag object representing the subtree with the
        current selection at the root"""

        if widget:
            drag = qt4.QDrag(self)
            mimedata = qt4.QMimeData()

            data = str('\n'.join((widget.typename,
                widget.name,
                widget.getSaveText())))
            mimedata.setText(data)
            drag.setMimeData(mimedata)

            clipboardData.setEncodedData(data)
            return clipboardData
        else:
            return None

    def slotWidgetCut(self, a):
        """Cut the selected widget"""
        self.slotWidgetCopy(a)
        self.slotWidgetDelete(a)
        self.updatePasteButton()

    def slotWidgetCopy(self, a):
        """Copy selected widget to the clipboard."""
        clipboard = qt4.qApp.clipboard()
        dragObj = self._makeDragObject(self.itemselected.widget)
        clipboard.setData(dragObj, clipboard.Clipboard)
        self.updatePasteButton()
        
    def slotWidgetPaste(self, a):
        """Paste something from the clipboard"""

        data = self.getClipboardData()
        if data:
            # The first line of the clipboard data is the widget type
            widgettype = data[0]
            # The second is the original name
            widgetname = data[1]

            # make the document enter batch mode
            # This is so that the user can undo this in one step
            op = document.OperationMultiple([], descr='paste')
            self.document.applyOperation(op)
            self.document.batchHistory(op)
            
            # Add the first widget being pasted
            self.makeWidget(widgettype, autoadd=False, name=widgetname)
            
            interpreter = self.parent.interpreter
        
            # Select the current widget in the interpreter
            tmpCurrentwidget = interpreter.interface.currentwidget
            interpreter.interface.currentwidget = self.itemselected.widget

            # Use the command interface to create the subwidgets
            for command in data[2:]:
                interpreter.run(command)
                
            # stop the history batching
            self.document.batchHistory(None)
                
            # reset the interpreter widget
            interpreter.interface.currentwidget = tmpCurrentwidget
            
    def slotWidgetDelete(self, a):
        """Delete the widget selected."""

        # no item selected, so leave
        if self.itemselected is None:
            return

        # work out which widget to delete
        w = self.itemselected.getAssociatedWidget()
            
        # get the item to next get the selection when this widget is deleted
        # this is done by looking down the list to get the next useful one
        next = self.itemselected
        while next is not None and (next.widget == w or (next.widget is None and
                                                     next.parent.widget == w)):
            next = next.itemBelow()

        # if there aren't any, use the root item
        if next is None:
            next = self.rootitem

        # remove the reference
        self.itemselected = None

        # delete selected widget
        self.document.applyOperation( document.OperationWidgetDelete(w) )

        # select the next widget
        self.listview.ensureItemVisible(next)
        self.listview.setSelected(next, True)

    def selectWidget(self, widget):
        """Select the associated listviewitem for the widget w in the
        listview."""
        
        # an iterative algorithm, rather than a recursive one
        # (for a change)
        found = False
        l = [self.listview.firstChild()]
        while len(l) != 0 and not found:
            item = l.pop()

            i = item.firstChild()
            while i is not None:
                if i.widget == widget:
                    found = True
                    break
                else:
                    l.append(i)
                i = i.nextSibling()

        assert found
        self.listview.ensureItemVisible(i)
        self.listview.setSelected(i, True)

    def slotWidgetMove(self, a, direction):
        """Move the selected widget up/down in the hierarchy.

        a is the action (unused)
        direction is -1 for 'up' and +1 for 'down'
        """

        # get the widget to act as the parent
        w = self.itemselected.getAssociatedWidget()

        # actually move the widget
        self.document.applyOperation( document.OperationWidgetMove(w, direction) )

        # try to highlight the associated item
        self.selectWidget(w)
        
    def slotListContextMenu(self, pos):
        """Pop up a context menu when an item is clicked on the list view."""

        self.contextpopup.exec_loop(pos)

    def updatePasteButton(self):
        """Is the data on the clipboard a valid paste at the currently
        selected widget?"""
        
        data = self.getClipboardData()
        show = False
        if data:
            # The first line of the clipboard data is the widget type
            widgettype = data[0]
            # Check if we can paste into the current widget or a parent
            if self.getSuitableParent(widgettype, self.itemselected.widget):
                show = True

        self.editactions['paste'].enable(show)

    def slotWidgetRename(self, action):
        """Initiate renaming a widget."""

        item = self.itemselected
        while item.widget is None:
            item = item.parent

        item.rename()

    def slotSelectWidget(self, widget):
        """The plot window says that a widget was selected, so we
        select it in the listview."""

        self.listview.selectWidget(widget)
        
