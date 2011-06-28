#! /usr/bin/python

import pyinotify, json, os, commands, backup, sys, signal

wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE  # watched events
remotepath = "/test"
localwatches = []

class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        if event.dir:
	  localwatches.append(wm2.add_watch(event.pathname, mask, rec=True));
	  print "create", event.pathname
	  backup.uploadMultipleFiles(event.pathname, remotepath)

    def process_IN_DELETE(self, event):
	print "remove", event.pathname
	#backup.deleteFileByPath(event.pathname, remotepath)
	print "Not deleting remotely"
        
    def process_IN_CLOSE_WRITE(self, event):
	print "close write"
	if os.path.exists(event.pathname):
	  print "modify", event.pathname
	  backup.uploadMultipleFiles(event.pathname, remotepath)
	else:
	  print "remove", event.pathname
	  #backup.deleteFileByPath(event.pathname, remotepath)
	  print "Not deleting remotely"

syncpath = '/tmp/testsync'
notifier = pyinotify.ThreadedNotifier(wm, EventHandler())
mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE 
wdd = wm.add_watch(syncpath, mask)
notifier.start()
print "Now watching", syncpath

def signal_handler(signal, frame):
        print 'Exiting'
        notifier.stop()
        sys.exit(0)



# do a sync
print "Syncing files changed since last run"
backup.sync(syncpath, remotepath)

signal.signal(signal.SIGINT, signal_handler)
print 'Finished sync, just listening on changes'
signal.pause()
