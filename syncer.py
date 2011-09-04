import pyinotify


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
	  
    def process_IN_MOVED_TO(self, event):
	print "moved to ", event.pathname
	backup.uploadMultipleFiles(event.pathname, backup.remotepath)


class Syncer:
  
  def start ( self ):
    notifier = pyinotify.ThreadedNotifier(wm, EventHandler())
    wdd = wm.add_watch(backup.syncpath, mask)
    notifier.start()
    print "Now watching", backup.syncpath