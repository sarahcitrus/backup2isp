#! /usr/bin/python

import pyinotify, json, os, commands, backup, sys, signal

wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE  # watched events
localwatches = []

class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        if event.dir:
	  localwatches.append(wm.add_watch(event.pathname, mask, rec=True));
	  print "create", event.pathname
	  backup.uploadMultipleFiles(event.pathname, backup.remotepath)
	else:
	  # upload symlink, close write doesnt catch this
	  if os.path.islink( event.pathname ):
	    backup.uploadMultipleFiles(event.pathname, backup.remotepath)
	    

    def process_IN_DELETE(self, event):
	print "remove", event.pathname
	#backup.deleteFileByPath(event.pathname, backup.remotepath)
	print "Not deleting remotely"
        
    def process_IN_CLOSE_WRITE(self, event):
	print "close write"
	if os.path.exists(event.pathname):
	  print "modify", event.pathname
	  backup.uploadMultipleFiles(event.pathname, backup.remotepath)
	else:
	  print "remove", event.pathname
	  #backup.deleteFileByPath(event.pathname, backup.remotepath)
	  print "Not deleting remotely"

notifier = pyinotify.ThreadedNotifier(wm, EventHandler())
mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE 
wdd = wm.add_watch(backup.syncpath, mask)
notifier.start()
print "Now watching", backup.syncpath

def signal_handler(signal, frame):
        print 'Exiting'
        notifier.stop()
        sys.exit(0)



# do a sync
print "Syncing files changed since last run"
backup.sync(backup.syncpath, backup.remotepath)

signal.signal(signal.SIGINT, signal_handler)
print 'Finished sync, just listening on changes'
signal.pause()
