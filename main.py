#! /usr/bin/python

import pyinotify, json, os, commands, backup, sys

wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE  # watched events

localwatches = []

class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        if event.dir:
	  localwatches.append(wm2.add_watch(event.pathname, mask, rec=True));
	  print "create", event.pathname
	  backup.uploadMultipleFiles(event.pathname)

    def process_IN_DELETE(self, event):
	print "remove", event.pathname
	backup.deleteFileByPath(event.pathname)
        
    def process_IN_CLOSE_WRITE(self, event):
	print "close write"
	if os.path.exists(event.pathname):
	  print "modify", event.pathname
	  backup.uploadMultipleFiles(event.pathname)
	else:
	  print "remove", event.pathname
	  backup.deleteFileByPath(event.pathname)

notifier = pyinotify.Notifier(wm, EventHandler())
mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE 
wdd = wm.add_watch('/tmp/testsync', mask)
try:
  notifier.loop()
except KeyboardInterrupt:
  print "Exiting"
  notifier.stop()
  sys.exit(1)