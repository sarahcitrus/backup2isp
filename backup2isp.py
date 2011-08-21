#! /usr/bin/python
import sys
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
	  if mainwin.isVisible():
	    mainwin.hide()
	  else:
	    mainwin.show()
      
   def confirmQuit(self):
       result = KMessageBox.questionYesNo(None, "Really quit?")
       if result == KMessageBox.Yes:
	app.quit()
       
       # closing this terminates the program
       


class LoginWindow(QtGui.QWidget):
  
    def __init__(self):
        super(LoginWindow, self).__init__()
        
        self.initUI()
        
    def initUI(self):
        
        username = QtGui.QLabel('Username')
        password = QtGui.QLabel('Password')

        providerBox = QtGui.QComboBox()
        providerBox.addItem('Virgin Media');
        
        usernameEdit = QtGui.QLineEdit()
        passwordEdit = QtGui.QLineEdit()
        passwordEdit.setEchoMode(QtGui.QLineEdit.Password)
        loginButton = QtGui.QPushButton('Login')

        grid = QtGui.QHBoxLayout()
        grid.addStretch(1)

        grid.addWidget(providerBox)
        grid.addWidget(username)
        grid.addWidget(usernameEdit)

        grid.addWidget(password)
        grid.addWidget(passwordEdit)
        
        
        grid.addWidget(loginButton)
        
        self.setLayout(grid)
        
        self.setWindowTitle("Backup2isp Login")
        self.show()
        self.move( KApplication.desktop().screen().rect().center() - self.rect().center() )

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

mainwin = LoginWindow()
mainwin.show()

tray = Systray()
sys.exit(app.exec_())