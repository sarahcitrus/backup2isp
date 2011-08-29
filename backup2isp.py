#! /usr/bin/python
import sys, os
from provider import Provider
from config import Config
from PyKDE4.kdeui import KApplication, KMainWindow, KMessageBox
from PyKDE4.kdecore import KCmdLineArgs, ki18n, KAboutData
from PyQt4 import QtCore, QtGui, Qt
from PyQt4.QtCore import Qt


class LocalDirTreeWidget(QtGui.QTreeWidget):

    def __init__(self,parent=None):

        QtGui.QTreeWidget.__init__(self,parent)

        itemList = []

        itemList.append("Path");
        
        self.items = {}
        self.selectedPaths = {}
        self.excludePaths = {}
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection);
        self.sortItems(0, Qt.AscendingOrder);
        self.setHeaderLabels(itemList);
        self.setUniformRowHeights(True);
        self.setAcceptDrops(True);
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        
    def expanded ( self, item ) :
        for x in range(0,item.childCount()):
	  child = item.child(x)
	  self.addDirTree ( child , str(child.toolTip(0)) )

    def checked ( self, item, column ) :
	if item.checkState(column) == Qt.Checked:
	  
	  if item.parent() == None or item.parent().checkState(0) != Qt.Checked:
	    # add if parent is unchecked, otherwise we would be covered by top-level check
	    self.selectedPaths[str(item.toolTip(0))] = True
	  if str(item.toolTip(0)) in self.excludePaths:
	    # if checked then it obviously isnt excluded
	    del self.excludePaths[str(item.toolTip(0))]
	    
	else:
	  if str(item.toolTip(0)) in self.selectedPaths:
	    # if unchecked need to make sure it isnt selected
	    del self.selectedPaths[str(item.toolTip(0))]
	  else:
	    if item.parent() != None and item.parent().checkState(0) == Qt.Checked: 
	      # if parent has is checked, then we want to exclude this dir
	      self.excludePaths[str(item.toolTip(0))] = True
	    else:
	      # if parent isnt checked, or is top-level dir, then no point excluding it any more
	      if str(item.toolTip(0)) in self.excludePaths:
		del self.excludePaths[str(item.toolTip(0))]
	  
	  # remove children from exclude list
	  for x in range(0,item.childCount()):
	    child = item.child(x)
	    if str(child.toolTip(0)) in self.excludePaths:
	      del self.excludePaths[str(child.toolTip(0))]	    
	
        for x in range(0,item.childCount()):
	  child = item.child(x)
	  child.setCheckState( column, item.checkState(column) )

    def addDirTree ( self, root, rootdir ):
	# get list of root dirs
	try:
	  items = os.listdir(rootdir)
	  for item in items:
	    dirpath =  os.path.join(rootdir,item)
	    if os.path.isdir( dirpath ) and not os.path.basename(dirpath).startswith('.'):
	      self.addItem( item, dirpath, False, root.checkState(0), root )
	except:
	  pass
	root.sortChildren(0, Qt.AscendingOrder)

    def initDirTree ( self, rootdir, selected ) :
	root = self.addItem(rootdir, rootdir,False,False)
	
	self.addDirTree( root,rootdir )
	self.connect(self, QtCore.SIGNAL("itemExpanded(QTreeWidgetItem *)"), self.expanded)
	self.connect(self, QtCore.SIGNAL("itemChanged(QTreeWidgetItem *, int)"), self.checked)
	

    def addItem ( self, name, data, expanded, checked, parent=None ) :
      
        # check if has item first
        if data in self.items:
	  return self.items[data]
      
	newitem = None
	if parent == None:
	  newitem = QtGui.QTreeWidgetItem(self)
	else:
	  newitem = QtGui.QTreeWidgetItem(None)
	if ( checked ) :
	  newitem.setCheckState(0,Qt.Checked);
	else:
	  newitem.setCheckState(0,Qt.Unchecked);
	  
        newitem.setText( 0, name )
        newitem.setToolTip( 0, data )
        
        #newitem.setData( 0, 0, data )
        #newitem.setValue( path )
	if parent != None:
	  parent.addChild( newitem )
	
	self.items[data] = newitem
	
	return newitem
      

class Systray(QtGui.QWidget):
   def __init__(self):
       QtGui.QWidget.__init__(self)
       self.createActions()
       self.createTrayIcon()
       self.trayIcon.show()

   def createActions(self):
       self.quitAction = QtGui.QAction(self.tr("&Quit"), self)
       QtCore.QObject.connect(self.quitAction, QtCore.SIGNAL("triggered()"), self.confirmQuit)
       
   def createTrayIcon(self):
       self.trayIconMenu = QtGui.QMenu(self)
       self.trayIconMenu.addAction(self.quitAction)

       self.trayIcon = QtGui.QSystemTrayIcon(self)
       self.trayIcon.setIcon(QtGui.QIcon("icon.svg"))
       self.trayIcon.setContextMenu(self.trayIconMenu)
       self.trayIcon.connect(self.trayIcon, QtCore.SIGNAL("activated(QSystemTrayIcon::ActivationReason)"), self.toggleMainWindow)

       
   def toggleMainWindow(self, reason):
       if reason == QtGui.QSystemTrayIcon.Trigger:
	  global mainwin
	  if mainwin.isVisible():
	    mainwin.hide()
	  else:
	    mainwin.show()
      
   def confirmQuit(self):
       result = KMessageBox.questionYesNo(None, "Really quit?")
       if result == KMessageBox.Yes:
	app.quit()
       
class ManagePaths(QtGui.QWidget):
  
    def __init__(self):
        super(ManagePaths, self).__init__()
        self.initUI()
        
    def initUI(self):
	global config
	self.localDirTree = LocalDirTreeWidget()
	self.localDirTree.initDirTree( "/", config.syncpaths )
	
        toplevel = QtGui.QHBoxLayout()
        toplevel.addWidget(self.localDirTree)
        
        gridv = QtGui.QVBoxLayout()
        gridv.addLayout(toplevel)
        self.setLayout(gridv)
        self.setWindowTitle("Backup2isp - Manage Sync Paths")
        self.move( KApplication.desktop().screen().rect().center() - self.rect().center() )
       
class BackupWindow(QtGui.QWidget):
  
    def __init__(self):
        super(BackupWindow, self).__init__()
        self.initUI()
        
    def beginBackup ( self ):
        global config
        if ( len(config.syncpaths) == 0 ):
	  self.updateProgress("No sync paths configured")
	  self.managePaths()
	else:
	  print config.syncpaths
    
    def manageBackups( self ):
	global choosebackuplocation
	choosebackuplocation.show()
    
    def managePaths( self ):
	global pathmanage
	pathmanage.show()
    
    def updateVolumeName ( self, detail ):
	self.backupVolumeTitle.setText(detail)
	
    def updateProgress ( self, detail ):
	self.progressDetail.setText(detail)
    
    def initUI(self):
	global config
        backupTitle = QtGui.QLabel('Backup Volume:')
        self.backupVolumeTitle = QtGui.QLabel(config.backupName)
	self.manageBackupButton = QtGui.QPushButton('Manage Backup Volumes')
	self.managePathsButton = QtGui.QPushButton('Manage Sync Paths')
	
        toplevel = QtGui.QHBoxLayout()
        toplevel.addWidget(backupTitle)
        toplevel.addWidget(self.backupVolumeTitle)
        toplevel.addWidget(self.manageBackupButton)
        
        secondlevel = QtGui.QHBoxLayout()
        progressTitle = QtGui.QLabel('Syncing Progress:')
        self.progressDetail = QtGui.QLabel('Stopped.')
        secondlevel.addWidget(progressTitle)
        secondlevel.addWidget(self.progressDetail)
        secondlevel.addWidget(self.managePathsButton)
        
        gridv = QtGui.QVBoxLayout()
        gridv.addLayout(toplevel)
        gridv.addLayout(secondlevel)
        self.setLayout(gridv)
        self.setWindowTitle("Backup2isp")
        self.move( KApplication.desktop().screen().rect().center() - self.rect().center() )
	self.manageBackupButton.connect(self.manageBackupButton, QtCore.SIGNAL("clicked()"), self.manageBackups)
	self.managePathsButton.connect(self.managePathsButton, QtCore.SIGNAL("clicked()"), self.managePaths)
        self.beginBackup()
        
    

class BackupLocationWindow(QtGui.QWidget):
    
    firstShow = True
    
    def __init__(self):
        super(BackupLocationWindow, self).__init__()
        self.firstShow = True
        self.initUI()
        
    def useBackup(self):
        global backupInstance, config, mainwin, backupwin
	resulttype, result = backupInstance.login( config.username, config.password, self.backupList.currentText() )
	if resulttype != "ERROR":
	  self.hide()
	  backupwin = BackupWindow()
	  mainwin = backupwin
	  mainwin.show()
	  backupwin.updateVolumeName( self.backupList.currentText() )
	else:
	  KMessageBox.error(None, result[0]['message'])
    
    def addBackup(self):
	global backupInstance, config
	text, result = QtGui.QInputDialog.getText(self, 'Add Backup', 'Backup Name:')
	if result:
	  resulttype, result = backupInstance.addBackup( str(text), config.workstation_id, config.workstation_name )
	  if resulttype != "ERROR":
	    KMessageBox.information(None, text + ' added.')
	    self.backupList.addItem(text)
	  else:
	    messagetext = result[0]['message']
	    if messagetext == "":
	      messagetext = result[0]['label']
	    KMessageBox.error(None, messagetext)
	
    def deleteBackup(self):
	global backupInstance
	boxresult = KMessageBox.questionYesNo(None, "Really delete backup '" + self.backupList.currentText() + "'?")
	if boxresult == KMessageBox.Yes:
	  resulttype, result = backupInstance.deleteBackup( str(self.backupList.currentText()) )
	  if result != "ERROR":
	    KMessageBox.information(None, self.backupList.currentText() + ' deleted.')
	    self.backupList.removeItem(self.backupList.currentIndex())
	  else:
	    KMessageBox.error(None, result[0]['message'])

    def event(self, event):
	if self.firstShow and event.type() == QtCore.QEvent.ActivationChange:
	  self.firstShow = False
	  if ( self.backupList.currentText() != "Select Backup" ):
	    self.useBackup()
	return super(BackupLocationWindow, self).event(event)
    
    def initUI(self):
        global backupInstance, config
        response, backups = backupInstance.listBackups()
        
        backupTitle = QtGui.QLabel('Backup')
        self.backupList = QtGui.QComboBox()
        self.useBackupButton = QtGui.QPushButton('Use')
        self.addBackupButton = QtGui.QPushButton('Add')
        self.deleteBackupButton = QtGui.QPushButton('Delete')
        
        i=1
        self.backupList.addItem("Select Backup")
        for backup in backups:
	  self.backupList.addItem(backups[backup]["backup_name"]);
	  # select stored backup
	  if backups[backup]["backup_name"] == config.backupName:
	    self.backupList.setCurrentIndex(i)
	  i+=1
        
        grid = QtGui.QHBoxLayout()
        grid.addWidget(backupTitle)
        grid.addStretch(1)
        grid.addWidget(self.backupList)
        grid.addWidget(self.useBackupButton)
        grid.addWidget(self.addBackupButton)
        grid.addWidget(self.deleteBackupButton)
        self.setLayout(grid)
        
        self.setWindowTitle("Backup2isp - Choose Backup")
        self.show()
        self.move( KApplication.desktop().screen().rect().center() - self.rect().center() )
        
        
	self.useBackupButton.connect(self.useBackupButton, QtCore.SIGNAL("clicked()"), self.useBackup)
	self.addBackupButton.connect(self.addBackupButton, QtCore.SIGNAL("clicked()"), self.addBackup)
	self.deleteBackupButton.connect(self.deleteBackupButton, QtCore.SIGNAL("clicked()"), self.deleteBackup)
        
    
    
class LoginWindow(QtGui.QWidget):
    
    loginButton = False
    providerBox = False
    usernameEdit = False
    passwordEdit = False
    firstShow = True
    
    def __init__(self):
        super(LoginWindow, self).__init__()
        self.firstShow = True
        self.initUI()
    
    def loginSubmit(self):
	self.loginButton.setEnabled(False)
	global backupInstance, config
	backupInstance = Provider.getInstance( self.providerBox.currentText(), config )
	resulttype, result = backupInstance.login( str(self.usernameEdit.text()), str(self.passwordEdit.text()), config.backupName )
	if resulttype != "ERROR":
	  # success
	  self.hide()
	  
	  global mainwin, choosebackuplocation
	  choosebackuplocation = BackupLocationWindow()
	  choosebackuplocation.show()
	  mainwin = choosebackuplocation
	else:
	  KMessageBox.error(None, result[0]['message'])
	
	self.loginButton.setEnabled(True)
        
    def event(self, event):
	if self.firstShow and event.type() == QtCore.QEvent.ActivationChange:
	  self.firstShow = False
	  if ( self.usernameEdit.text() and self.passwordEdit.text() ):
	    self.loginSubmit()
	return super(LoginWindow, self).event(event)
    
    def initUI(self):
        global config
        
        username = QtGui.QLabel('Username')
        password = QtGui.QLabel('Password')

        self.providerBox = QtGui.QComboBox()
        self.providerBox.addItem('Virgin Media');
        
        self.usernameEdit = QtGui.QLineEdit()
        self.usernameEdit.setText( config.username )
        
        self.passwordEdit = QtGui.QLineEdit()
        self.passwordEdit.setEchoMode(QtGui.QLineEdit.Password)
        self.passwordEdit.setText( config.password )
        self.loginButton = QtGui.QPushButton('Login')

        grid = QtGui.QHBoxLayout()
        grid.addStretch(1)

        grid.addWidget(self.providerBox)
        grid.addWidget(username)
        grid.addWidget(self.usernameEdit)

        grid.addWidget(password)
        grid.addWidget(self.passwordEdit)
        
        
        grid.addWidget(self.loginButton)
        
        self.usernameEdit.connect(self.usernameEdit, QtCore.SIGNAL("returnPressed()"), self.loginSubmit)
        self.passwordEdit.connect(self.passwordEdit, QtCore.SIGNAL("returnPressed()"), self.loginSubmit)
        self.loginButton.connect(self.loginButton, QtCore.SIGNAL("clicked()"), self.loginSubmit)
        
        self.setLayout(grid)
        
        self.setWindowTitle("Backup2isp Login")
        self.setFixedSize( 450,40 )
        self.show()
        self.move( KApplication.desktop().screen().rect().center() - self.rect().center() )

global backupInstance, choosebackuplocation, config, pathmanage
backupInstance = False
config = Config()

appName     = "Backup2isp"
catalog     = ""
programName = ki18n ("Backup2isp")
version     = "1.0"
description = ki18n ("Backup 2 ISP")
license     = KAboutData.License_GPL
copyright   = ki18n ("(c) 2011 Anonymous")
text        = ki18n ("ISP Backup software")
homePage    = "https://github.com/sarahcitrus/backup2isp"
bugEmail    = ""

aboutData   = KAboutData (appName, catalog, programName, version, description,
                        license, copyright, text, homePage, bugEmail)

KCmdLineArgs.init (sys.argv, aboutData)
app = KApplication ()
kmainwin = KMainWindow()

loginwin = LoginWindow()
pathmanage = ManagePaths()
global mainwin
mainwin = loginwin

tray = Systray()
sys.exit(app.exec_())