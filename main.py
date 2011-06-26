#! /usr/bin/python

import pyinotify, json, os, commands, backup, sys, signal

wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE  # watched events

localwatches = []

class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        if event.dir:
	  localwatches.append(wm2.add_watch(event.pathname, mask, rec=True));
	  print "create", event.pathname

    def process_IN_DELETE(self, event):
	print "remove", event.pathname
        
    def process_IN_CLOSE_WRITE(self, event):
	if os.path.exists(event.pathname):
	  print "modify", event.pathname
	else:
	  print "remove", event.pathname

def signal_handler(signal, frame):
        print "Quitting"
        sys.exit(0)
        
notifier = pyinotify.ThreadedNotifier(wm, EventHandler())
wdd = wm.add_watch('/tmp/testsync', pyinotify.IN_CLOSE_WRITE)

signal.signal(signal.SIGINT, signal_handler)
print 'Listening for changes, Ctrl+C to abort'
signal.pause()
notifier.stop()