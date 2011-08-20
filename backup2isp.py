#! /usr/bin/python

import sys

from PyKDE4.kdeui import KNotification, KSystemTrayIcon, KIcon, KStandardAction, KToggleAction, KApplication, KMenu, KMessageBox, KStandardGuiItem
from PyKDE4.kdecore import ki18n, KAboutData, KCmdLineArgs
from PyQt4.QtCore import SIGNAL, QObject
from PyQt4 import QtGui
from PyQt4 import QtCore
 

def confirmClose():
  response = KMessageBox.questionYesNo(None, "Really quit?", "test", KStandardGuiItem.yes(), KStandardGuiItem.cancel() )
  if response == 3:
    print "Yes"
    return True
  else:
    print "No"
    return False

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

ICON_FILE = "/usr/share/pixmaps/monitor.png"
icon = KSystemTrayIcon(ICON_FILE)
icon.setToolTip("Running")

menu = QtGui.QMenu()
exitAction = QtGui.QAction(QtGui.QIcon(":/icons/icons/exit.png"), (u"Exit"), None)

QtCore.QObject.connect(exitAction, QtCore.SIGNAL("triggered(bool)"), confirmClose)
menu.addAction(exitAction)
icon.setContextMenu(menu)

icon.show()

#Start the evnt loop
sys.exit(app.exec_())