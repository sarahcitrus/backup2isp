import ConfigParser, socket, hashlib, os

class Config():
  
  def __init__( self ):
    self.workstation_name = socket.gethostname();
    self.workstation_id = hashlib.md5(self.workstation_name).hexdigest();
    self.configdir = ".backup2isp"
    self.tokenfilename = "token"
    self.configpath = os.path.join(os.getenv("HOME"), self.configdir)
    self.configfile = os.path.join( self.configpath, "config" )
    self.tokenfile = os.path.join(self.configpath, self.tokenfilename)
    self.config = ConfigParser.ConfigParser()
    if os.path.exists( self.configfile ):
      self.config.readfp( open(self.configfile) )
      
    self.useragent = self.config.get('Server', 'useragent')
    self.server = self.config.get('Server', 'server')
    self.dac = self.config.get('Server', 'dac')
    self.provider = self.config.get('Server', 'provider')
    self.username = self.config.get('Server', 'username')
    self.password = self.config.get('Server', 'password')
    self.backupName = self.config.get('Local', 'backupname')
    self.remotepath = self.config.get('Local', 'remotepath')
    self.syncpath = self.config.get('Local', 'localpath')
    self.tokenexpiry = 0