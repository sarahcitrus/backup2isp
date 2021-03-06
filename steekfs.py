#! /usr/bin/env python2
import fuse, sys, logging, logging.handlers, posix
fuse.fuse_python_api = (0, 2)
from fuse import Fuse
from config import Config

from provider import Provider

import stat,os,errno,time


logfile = "/var/log/steekfs.log"
logging.basicConfig(filename=logfile,level=logging.DEBUG)

def dirFromList(list):
    """
    Return a properly formatted list of items suitable to a directory listing.
    [['a', 'b', 'c']] => [[('a', 0), ('b', 0), ('c', 0)]]
    """
    return [[(x, 0) for x in list]]

def getDepth(path):
    """
    Return the depth of a given path, zero-based from root ('/')
    """
    """
    if path <code></code> '/':
        return 0
    else:
        return path.count('/')
    """
    pass

def getParts(path):
    """
    Return the slash-separated parts of a given path as a list
    """
    """
    if path <code></code> '/':
        return [['/']]
    else:
        return path.split('/')
    """
    pass

class SteekStat(fuse.Stat):
  def __init__(self):
      self.st_mode = stat.S_IFDIR | 0755
      self.st_ino = 0
      self.st_dev = 0
      self.st_nlink = 2
      self.st_uid = 0
      self.st_gid = 0
      self.st_size = 4096
      self.st_atime = 0
      self.st_mtime = 0
      self.st_ctime = 0

class SteekFS(Fuse):
    """
    """
    dirCache = {}
    
    def invalidateDirCache ( self, path ):
	dirpath = os.path.dirname(path).strip('/')
	if dirpath in self.dirCache:
	  del self.dirCache[dirpath]
	  logging.debug("%s - %s" % ('dir cache removed', dirpath ) )

    def __init__(self, backup,*args, **kw):
        Fuse.__init__(self, *args, **kw)
        config = Config()
        self.provider = Provider.getInstance('Virgin Media', config)
	resulttype, result = self.provider.login( config.username, config.password, backup )
	if resulttype != "ERROR":
	  print 'Init complete.'
	else:
	  print result[0]['message']


    def getattr(self, path):
	logging.debug("%s - %s" % ('getattr', path ) )
        st = SteekStat()
	if path == "/":
	  return st
        name = os.path.basename(path)
	dirlist = self.readdir( os.path.dirname(path) , 0)
	
	found=False
	
	for filedetail in dirlist:
	  if filedetail.name == name:
	    found=True
	    st.st_mode = filedetail.type
	    st.steek_id = filedetail.steek_id
	    if st.st_mode & stat.S_IFREG:
	      st.st_nlink = 1
	      st.st_size = filedetail.size
	    break

	if found == False:
	  return -errno.ENOENT
	  
	st.st_atime = filedetail.date
	st.st_mtime = filedetail.date
	st.st_ctime = filedetail.date

	return st
	
    def readdir(self, path, offset):
	logging.debug("%s - %s - %i" % ('readdir', path, offset ) )
	if not path.strip('/') in self.dirCache: 
	  files = self.provider.listFiles(path)
	  self.dirCache[path.strip('/')] = files
	else:
	  files = self.dirCache[path.strip('/')]
	
	dirents = [ { 'type' : 'd', 'name' : '.', 'size' : 4096, 'date' : int(time.time()), 'steek_id' : -1 } , 
		    { 'type' : 'd', 'name' : '..', 'size' : 4096, 'date' : int(time.time()), 'steek_id' : -1 } ]
	dirents.extend(files)
	count=0
	for r in dirents:
	  if count < offset:
	    count+=1
	    continue
	  count+=1
	  entry = fuse.Direntry(r['name'])
	  entry.size = r['size']
	  entry.date = r['date']
	  entry.steek_id = r['steek_id']
	  if r['type'] == 'd':
	    entry.type = ( stat.S_IFDIR | 0755 )
	  elif r['type'] == 'f':
	    entry.type = ( stat.S_IFREG | 0666 )
	  yield entry

    def open ( self, path, flags ):
        result = self.getattr(path)
        if type(result) != SteekStat:
	  return -errno.ENOENT

    def read ( self, path, length, offset ):
	logging.debug("%s - %s - %i - %i" % ('read', path, length, offset ) )
	result = self.getattr(path)
	if type(result) != SteekStat:
	  return -errno.ENOENT
	else:
	  data = self.provider.readFileById(result.steek_id, length, offset, result.st_size)
	  return data

    def truncate ( self, path, size ):
        if size == 0:
	  logging.debug("%s - %s - %i" % ('truncate', path, size ) )
	  return self.write(path,"", 0)
	else:
	  logging.debug("UNIMPLEMENTED %s - %s - %i" % ('truncate', path, size ) )
	  return -errno.ENOSYS

    def mknod ( self, path, mode, dev ):
	if dev == 0:
	  logging.debug("%s - %s - %s - %s" % ('mknod', path, oct(mode), dev ) )
	  return self.write(path, '', 0)
	else:
	  logging.debug("UNIMPLEMENTED %s - %s - %s - %s" % ('mknod', path, oct(mode), dev ) )
	  return -errno.ENOSYS
        
    def write ( self, path, buf, offset ):
	if offset == 0:
	  logging.debug("%s - %s - %i - %i" % ('write', path, len(buf), offset ) )
	  result = self.provider.writeToPath( path, buf, offset )
	  self.invalidateDirCache(path)
	  return result
	else:
	  logging.debug("UNIMPLEMENTED %s - %s - %i - %i" % ('write', path, len(buf), offset ) )
	  return -errno.ENOSYS

    def unlink ( self, path ):
        logging.debug("%s - %s" % ('unlink', path ) )
        result = self.getattr(path)
        if type(result) != SteekStat:
	  return -errno.ENOENT
	else:
	  if result.st_mode & stat.S_IFDIR:
	    result = self.provider.deleteFileById(result.steek_id, 'd')
	  else:
	    result = self.provider.deleteFileById(result.steek_id, 'f')
	  self.invalidateDirCache(path)
	  return 0

    def rmdir ( self, path ):
        logging.debug("%s - %s" % ('rmdir', path ) )
        return self.unlink(path)
        
    def fsync ( self, path, isFsyncFile ):
	# cant implement, dont have a local write cache
        pass

    def statfs ( self ):
        logging.debug("%s" % ('statfs' ) )
        maxspace, spaceused = self.provider.statfs()
        
        if maxspace == -1:
	  maxspace = (1024*1024*1024*1024*1024) # 1pb
        
        blocksize=1048576 # 1mb blocks
        fragment=1
        blockstotal=maxspace/blocksize
        blocksfree=blockstotal-(spaceused/blocksize)
        nodestotal=blockstotal
        nodesfree=blocksfree
        flag=1024
        filenamelength=255
        result = posix.statvfs_result((blocksize,
				       fragment,
				       blockstotal,
				       blocksfree,
				       blocksfree,
				       nodestotal,
				       nodesfree,
				       nodesfree,
				       flag,
				       filenamelength))
        return result
        
    def link ( self, targetPath, linkPath ):
        logging.debug("%s - %s - %s" % ('link', targetPath, linkPath ) )
        return self.symlink(targetPath, linkPath)
        
    def mkdir ( self, path, mode ):
        logging.debug("%s - %s - %s" % ('mkdir', path, oct(mode) ) )
	result = self.provider.makeDir(path)
	self.invalidateDirCache(path)
	return result
        
    def rename ( self, oldPath, newPath ):
        logging.debug("%s - %s - %s" % ('rename', oldPath, newPath ) )
        return self.provider.renameFile(oldPath, newPath)
        
    def chmod ( self, path, mode ):
        logging.debug("UNIMPLEMENTED %s - %s - %s" % ('chmod', path, oct(mode)) )
        return -errno.ENOSYS

    def chown ( self, path, uid, gid ):
        logging.debug("UNIMPLEMENTED %s - %s - %i - %i" % ('chown', path, uid, gid) )
        return -errno.ENOSYS

    def readlink ( self, path ):
        logging.debug("UNIMPLEMENTED %s - %s" % ('readlink', path ) )
        return -errno.ENOSYS

    def release ( self, path, flags ):
        logging.debug("UNIMPLEMENTED %s - %s - %i" % ('release', path, flags ) )
        return -errno.ENOSYS


    def symlink ( self, targetPath, linkPath ):
        logging.debug("UNIMPLEMENTED %s - %s - %s" % ('symlink', targetPath, linkPath ) )
        return -errno.ENOSYS

    def utime ( self, path, times ):
        logging.debug("UNIMPLEMENTED %s - %s - %s" % ('utime', path, times ) )
        return -errno.ENOSYS
        
if __name__ == '__main__':
    usage = "Usage: steekfs.py backup /mount/path"
    if(len(sys.argv) < 2):
	    raise Exception(usage)
    backup = sys.argv[1]
    dir = sys.argv[2]

    # fix params
    sys.argv = ['steekfs.py', dir]
	  
    fs = SteekFS(backup, version="PythonS3",
                                         usage=usage,
                                         dash_s_do='setsingle')
    fs.parse(errex=1)
    #print fs.getattr('/')
    #for item in fs.readdir('/', 0):
    #  print item.name, item.size, item.type, item.date
    fs.main()
