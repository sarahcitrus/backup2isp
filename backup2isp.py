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
       self.trayIcon.setIcon(QtGui.QIcon("/usr/share/pixmaps/monitor.png"))
       self.trayIcon.setContextMenu(self.trayIconMenu) 
      
   def confirmQuit(self):
       result = KMessageBox.questionYesNo(None, "Really quit?")
       if result == KMessageBox.Yes:
	print "Quitting"
	app.quit()
       else:
	print "Not quitting"
       
       # closing this terminates the program
       
       
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
mainwin = KMainWindow()
tray = Systray()
sys.exit(app.exec_())