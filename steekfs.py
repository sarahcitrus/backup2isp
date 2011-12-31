#!/usr/bin/python
import fuse, sys
fuse.fuse_python_api = (0, 2)
from fuse import Fuse
from config import Config

from provider import Provider

import stat,os,errno,time


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
        """
        - st_mode (protection bits)
        - st_ino (inode number)
        - st_dev (device)
        - st_nlink (number of hard links)
        - st_uid (user ID of owner)
        - st_gid (group ID of owner)
        - st_size (size of file, in bytes)
        - st_atime (time of most recent access)
        - st_mtime (time of most recent content modification)
        - st_ctime (platform dependent; time of most recent metadata change on Unix,
                    or the time of creation on Windows).
        """      
        st = SteekStat()
        name = os.path.basename(path)
	dirlist = self.readdir( os.path.dirname(path) , 0)
	for filedetail in dirlist:
	  if filedetail.name == name:
	    st.st_mode = filedetail.type
	    if st.st_mode & stat.S_IFREG:
	      st.st_nlink = 1
	      st.st_size = filedetail.size
	    break

	st.st_atime = int(time.time())
	st.st_mtime = st.st_atime
	st.st_ctime = st.st_atime

	return st
	
    def readdir(self, path, offset):
	if not path in self.dirCache: 
	  files = self.provider.listFiles(path)
	  self.dirCache[path] = files
	else:
	  files = self.dirCache[path]
	
	dirents = [ { 'type' : 'd', 'name' : '.'} , { 'type' : 'd', 'name' : '..'} ]
	dirents.extend(files)
	
	for r in dirents:
	  entry = fuse.Direntry(r['name'])
	  if r['type'] == 'd':
	    entry.type = ( stat.S_IFDIR | 0755 )
	  elif r['type'] == 'f':
	    entry.type = ( stat.S_IFREG | 0666 )
	    entry.size = r['size']
	  yield entry

    def mythread ( self ):
        print '*** mythread'
        return -errno.ENOSYS

    def chmod ( self, path, mode ):
        print '*** chmod', path, oct(mode)
        return -errno.ENOSYS

    def chown ( self, path, uid, gid ):
        print '*** chown', path, uid, gid
        return -errno.ENOSYS

    def fsync ( self, path, isFsyncFile ):
        print '*** fsync', path, isFsyncFile
        return -errno.ENOSYS

    def link ( self, targetPath, linkPath ):
        print '*** link', targetPath, linkPath
        return -errno.ENOSYS

    def mkdir ( self, path, mode ):
        print '*** mkdir', path, oct(mode)
        return -errno.ENOSYS

    def mknod ( self, path, mode, dev ):
        print '*** mknod', path, oct(mode), dev
        return -errno.ENOSYS

    def open ( self, path, flags ):
        print '*** open', path, flags
        return -errno.ENOSYS

    def read ( self, path, length, offset ):
        print '*** read', path, length, offset
        return -errno.ENOSYS

    def readlink ( self, path ):
        print '*** readlink', path
        return -errno.ENOSYS

    def release ( self, path, flags ):
        print '*** release', path, flags
        return -errno.ENOSYS

    def rename ( self, oldPath, newPath ):
        print '*** rename', oldPath, newPath
        return -errno.ENOSYS

    def rmdir ( self, path ):
        print '*** rmdir', path
        return -errno.ENOSYS

    def statfs ( self ):
        print '*** statfs'
        return -errno.ENOSYS

    def symlink ( self, targetPath, linkPath ):
        print '*** symlink', targetPath, linkPath
        return -errno.ENOSYS

    def truncate ( self, path, size ):
        print '*** truncate', path, size
        return -errno.ENOSYS

    def unlink ( self, path ):
        print '*** unlink', path
        return -errno.ENOSYS

    def utime ( self, path, times ):
        print '*** utime', path, times
        return -errno.ENOSYS

    def write ( self, path, buf, offset ):
        print '*** write', path, buf, offset
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
    #  print item
    fs.main()