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
    self.useragent = 'AGBackup-VirginMedia-en_EN-v2.3.1.31082-AGBK_VIRGIN_W-Backup n Storage-WIN_Seven-?-DG'
    self.server = 'cl-virgin.ob.f-secure.com'
    self.dac = 'AGD44cdx56rtt7u8'
    self.provider = None
    self.username = ""
    self.password = ""
    self.backupName = ""
    self.remotepath = "/"
    self.syncpaths = []
    self.tokenexpiry = 0
    
    self.config = ConfigParser.ConfigParser()
    if not os.path.exists( self.configfile ):
      # config file doesnt exist, create one with default options, have user fill in blanks
      self.config.add_section('Version')
      self.config.set("Version", "version", 1 )
      
      self.config.add_section('Server')
      self.config.set('Server', 'useragent', 'AGBackup-VirginMedia-en_EN-v2.3.1.31082-AGBK_VIRGIN_W-Backup n Storage-WIN_Seven-?-DG')
      self.config.set('Server', 'server', 'cl-virgin.ob.f-secure.com')
      self.config.set('Server', 'dac', 'AGD44cdx56rtt7u8')
      
      self.config.set('Server', 'provider', "")
      self.config.set('Server', 'username', "")
      self.config.set('Server', 'password', "")
  
      self.config.add_section('Local')
      self.config.set('Local', 'localpaths', [])
      self.config.set('Local', 'remotepath', "/")
      self.config.set('Local', 'backupname', "")
    
      # Writing our configuration file to 'example.cfg'
      with open(self.configfile, 'wb') as configdetail:
	  self.config.write(configdetail)
      
    self.config.readfp( open(self.configfile) )
    self.useragent = self.config.get('Server', 'useragent')
    self.server = self.config.get('Server', 'server')
    self.dac = self.config.get('Server', 'dac')
    self.provider = self.config.get('Server', 'provider')
    self.username = self.config.get('Server', 'username')
    self.password = self.config.get('Server', 'password')
    self.backupName = self.config.get('Local', 'backupname')
    self.remotepath = self.config.get('Local', 'remotepath')
    self.syncpaths = self.config.get('Local', 'localpaths')
    self.tokenexpiry = 0

  def saveConfig (self ):
    self.config.set('Local', 'backupname', self.backupName)
    self.config.set('Server', 'username', self.username)
    self.config.set('Server', 'password', self.password)
    with open(self.configfile, 'wb') as configdetail:
      self.config.write(configdetail)