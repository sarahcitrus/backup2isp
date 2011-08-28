#! /usr/bin/python
import sys
from provider import Provider
from config import Config
from PyKDE4.kdeui import KApplication, KMainWindow, KMessageBox
from PyKDE4.kdecore import KCmdLineArgs, ki18n, KAboutData
from PyQt4 import QtCore, QtGui

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
       
       
class BackupWindow(QtGui.QWidget):
  
    def __init__(self):
        super(BackupWindow, self).__init__()
        self.initUI()
        
    def beginBackup ( self ):
        global config
        print config.syncpaths
        if ( len(config.syncpaths) == 0 ):
	  self.updateProgress("No sync paths configured")
    
    def manageBackups( self ):
	global choosebackuplocation
	choosebackuplocation.show()
    
    def updateVolumeName ( self, detail ):
	self.backupVolumeTitle.setText(detail)
	
    def updateProgress ( self, detail ):
	self.progressDetail.setText(detail)
    
    def initUI(self):
	global config
        backupTitle = QtGui.QLabel('Backup Volume:')
        self.backupVolumeTitle = QtGui.QLabel(config.backupName)
	self.manageBackupButton = QtGui.QPushButton('Manage Backup Volumes')
	
        toplevel = QtGui.QHBoxLayout()
        toplevel.addWidget(backupTitle)
        toplevel.addWidget(self.backupVolumeTitle)
        toplevel.addWidget(self.manageBackupButton)
        
        secondlevel = QtGui.QHBoxLayout()
        progressTitle = QtGui.QLabel('Syncing Progress:')
        self.progressDetail = QtGui.QLabel('Stopped.')
        secondlevel.addWidget(progressTitle)
        secondlevel.addWidget(self.progressDetail)
        
        gridv = QtGui.QVBoxLayout()
        gridv.addLayout(toplevel)
        gridv.addLayout(secondlevel)
        self.setLayout(gridv)
        self.setWindowTitle("Backup2isp")
        self.move( KApplication.desktop().screen().rect().center() - self.rect().center() )
	self.manageBackupButton.connect(self.manageBackupButton, QtCore.SIGNAL("clicked()"), self.manageBackups)
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

global backupInstance, choosebackuplocation, config
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
global mainwin
mainwin = loginwin

tray = Systray()
sys.exit(app.exec_())