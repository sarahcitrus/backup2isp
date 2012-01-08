import httplib, urllib, mimetools, re, time, os, pickle, datetime, logging, errno, mimetypes, hashlib

class Steek:
  
  tokenexpiry = 0
  config = False
  token = False
  backup = None
  loginFormName = "AYMARA"
  ticketFormName = "DUNGEONTICKET"
  deviceName = 'DUNGEONDEVICE'
  provider = 'virgin'
  server = 'cl-virgin.ob.f-secure.com'
  dac = 'AGD44cdx56rtt7u8'
  useragent = 'AGBackup-VirginMedia-en_EN-v2.3.1.31082-AGBK_VIRGIN_W-Backup n Storage-WIN_Seven-?-DG'

  def __init__ ( self, config):
    self.config = config

  def login ( self, username, password, backup, skipCheck=None ) :
    if skipCheck != True:
      if username == self.config.username and password == self.config.password and backup == self.config.backupName:
	
	self.username = username
	self.password = password
	self.backup = backup
	self.getToken()
	return "META", []
    
    self.username = username
    self.config.username = username
    self.password = password
    self.config.password = password
    self.backup = backup
    self.config.backupName = backup
    self.config.save()
    
    self.token = False
    if backup == None:
      meta = self.generateMeta( "sso_mode", { 'sso_mode' : self.provider } , 
		  "login", { 'login' : username, 'password' : password } ) + "#"
    else:
      meta = self.generateMeta( "sso_mode", { 'sso_mode' : self.provider } , 
		  "login", { 'login' : username, 'password' : password, 'backup_name' : backup } ) + "#"
		  
    status, results = self.doTicket( "LOGIN_BY_SSO", self.loginFormName, meta )
    if status == "META":
      self.token = results[0]["session"]
      self.tokenexpiry = int(results[0]["duration"]) + int(time.time())
      
      f = open(self.config.tokenfile, "w")
      pickle.dump( ( self.backup, self.tokenexpiry, self.token ) , f)
      f.close()
      
    return status, results
  
  def getToken ( self ):
    if not self.token:
    
      if os.path.exists( self.config.tokenfile ):
	print "Checking existing token"
	f = open(self.config.tokenfile, "r")
	savedbackup, savedtime, savedtoken = pickle.load(f)
	f.close()
	if self.backup != savedbackup:
	  print "Different backup, getting new auth token"
	  self.login(self.username, self.password, self.backup, True)
	else:
	  if savedtime >= time.time():
	    tokenexpiry = savedtime
	    self.config.backupName = savedbackup
	    self.tokenexpiry = savedtime
	    self.token = savedtoken
	  else:
	    print "Token expired"
	    self.login(self.username, self.password, self.backup, True)
      else:
	print "No existing token"
	self.login(self.username, self.password, self.backup, True)
    
    return self.token, self.tokenexpiry
  
  def readFileById ( self, id, length, offset, size ):
    self.getToken()
    
    if size == 0 or offset >= size:
      return ''
    
    start = offset
    end = offset+length
    
    if offset + length >= size:
      end = size
    
    end-=1
      
    headers = {"User-Agent": self.useragent, "Accept" : "*/*", "Range" : "bytes=" + str(start) + "-" + str(end) }
    connection = httplib.HTTPSConnection(self.server)
    #connection.set_debuglevel(9)
    connection.request("POST", "/gate/download.php" + "?id=" + id + "&ticket=" +  self.token, None, headers)
    response = connection.getresponse()
    if response.status == 206:
      data = response.read(length)
      connection.close()
      return data
    else:
      logging.error(str(headers) + str(response.getheaders()) + "\n" + response.read())
      return -errno.EIO
  
  def deleteFileById ( self, id, type ):
    self.getToken()
    
    return self.doTicket("DELETE", self.loginFormName, self.generateMetaList( { "ids" : ( id, ), "types" : (type,) } ) )
    
  def renameFile ( self, oldPath, newPath ):
    self.getToken()
    commandform = { 'name': 'command', 'data' : "RENAME" }
    initform = { 'name': 'init', 'data' : "13000" }
    option1 = { 'name': 'option1', 'data' : "" }
    option2 = { 'name': 'option2', 'data' : "" }
    param1 = { 'name': 'param1', 'data' : oldPath }
    param2 = { 'name': 'param2', 'data' : newPath }
    param3 = { 'name': 'param3', 'data' : oldPath }
    param4 = { 'name': 'param4', 'data' : newPath }
    
    extraForms = [commandform, initform, option1, option2, param1, param2]
    
    details = self.doTicket("RENAME", self.loginFormName, None, extraForms )
    print details
  
  def statfs( self ):
    info = self.doTicket("INFO",  self.loginFormName)
    results = {}
    for item in info.split('|'):
      detail = item.split('=')
      results[detail[0]] = detail[1]
    return int(results["SPACE_MAX"]), int(results["SPACE_USED"])
  
  def makeDir ( self, path ):
    return self.writeToPath( os.path.join(path,'.keep'), "", 0 )
  
  def writeToPath ( self, path, buf, offset ) :
    self.getToken()
    contenttypetext = "text/plain"
    filename = os.path.basename(path)
    path = os.path.dirname(path).strip('/')
    
    sha1hash = hashlib.sha1();
    sha1hash.update(buf)
    
    sha1 = sha1hash.hexdigest().upper()

    commandform = { 'name': 'command', 'data' : "PUT" }
    initform = { 'name': 'init', 'data' : "13000" }
    option1 = { 'name': 'option1', 'data' : "O" } # O (not zero) is overwrite
    option2 = { 'name': 'option2', 'data' : time.strftime("%Y-%m-%d %H:%M:%S") } # date
    option3 = { 'name': 'option3', 'data' : "15" }
    option4 = { 'name': 'option4', 'data' : "0" }
    option5 = { 'name': 'option5', 'data' : "2|#type=1|0|#hidden=1|0|#system=1|0|#readonly=1|0|#permissions=1|0|#;" } # metadata
    option6 = { 'name': 'option6', 'data' : "SHA1:" + sha1 } # sha of file uploading
    option7 = { 'name': 'option7', 'data' : "NOT_CRYPTED" } # encryption method
    option8 = { 'name': 'option8', 'data' : "0" } # something to do with the length of the file , changes a param when listing
    param1 = { 'name': 'param1', 'data' : path } # destination dir
    param2 = { 'name': 'param2', 'data' : filename } # filename
    filedetail = { 'name': 'file', 'data' : "Content-Type: " + contenttypetext + "\r\n\r\n", 'filename' : filename }
    extraForms = [commandform, initform, option1, option2, option3, option4, option5, option6, option7, option8, param1, param2, filedetail ]
    conn, boundary, formdata, headers = self.doTicket("PUT", self.loginFormName, None, extraForms )
    #conn.set_debuglevel(9)
    finalstring = "\r\n------------------------------" + boundary + "--"
    conn.putrequest("POST", "/gate/dungeongate.php")
    headers["Content-Length"] = len( formdata ) + len(buf) + len(finalstring);
    for item in headers.keys():
      conn.putheader( item, headers[item] )
    conn.endheaders()
    conn.send(formdata)
    
    
    if len(buf) > 0:
      conn.send( buf )
    conn.send(finalstring)
    
    response = conn.getresponse()
    data = response.read()
    conn.close()
    if data[0:5] == "ERROR":
      print data
      logging.error(str(headers) + str(formdata) + data)
      return -errno.EIO
      
    return len(buf)
  
  def getFileToPath ( self, path, localpath ) :
    self.getToken()
    filename = os.path.basename(path)
    path = os.path.dirname(path)
    
    commandform = { 'name': 'command', 'data' : "GET" }
    initform = { 'name': 'init', 'data' : "13000" }
    param1 = { 'name': 'param1', 'data' : path }
    param2 = { 'name': 'param2', 'data' : filename }
    extraForms = [commandform, initform,param1, param2]
    conn, response = self.doTicket("GET", self.loginFormName, None, extraForms )
    
    localfile = open(localpath,"w")
    buffersize=8096
    while True:
      datapart = response.read(buffersize)
      if not datapart:
	  break
      localfile.write(datapart)
    
    localfile.close()
    conn.close()
    return True
  
  def listFiles ( self, path ) :
    self.getToken()
    
    commandform = { 'name': 'command', 'data' : "LIST" }
    initform = { 'name': 'init', 'data' : "13000" }
    option1 = { 'name': 'option1', 'data' : "" }
    option2 = { 'name': 'option2', 'data' : "" }
    param1 = { 'name': 'param1', 'data' : path }
    
    extraForms = [commandform, initform, option1, option2, param1]
    
    details = self.doTicket("LIST", self.loginFormName, None, extraForms )
    details = details.split("\n")
    # convert files to list
    fulllist = []
    if len(details) > 1:
      for detail in details:
	if len(detail) >0 :
	  fulllist.append(self.parseFile(detail))
    return fulllist

  def parseFile ( self, data ):
    details = data.split('|')
    resultdetail = {}
    resultdetail['steek_id'] = details[6]
    resultdetail['name'] = details[1]
    resultdetail['type'] = 'd'
    resultdetail['size'] = 4096
    datestruct = time.strptime(details[5], "%Y-%m-%d %H:%M:%S")
    resultdetail['date'] = int(time.mktime(datestruct))
    if details[0].find('F') != -1:
      resultdetail['type'] = 'f'
      resultdetail['size'] = int(details[2])
    return resultdetail
    
  def listBackups ( self ) : 
    self.getToken()
    return self.doTicket("LSMYBACKUPS",  self.loginFormName)
    
  def deleteBackup( self, name ):
    return self.doTicket("REMOVEBACKUP", self.loginFormName, self.generateMeta( "backup_name", { "backup_name" : name } , 
						"session_name", 
						{ "session_name" : "user",
						"notification" : 1 } ) )
      
  def addBackup( self, name, workstation_id, workstation_name ):
    return self.doTicket("ADDBACKUP", self.loginFormName, self.generateMeta( "backup_name", { "backup_name" : name,
						"workstation_id" : workstation_id, 
						"workstation_name" : workstation_name } , 
						"session_name", 
						{ "session_name" : "user",
						"notification" : 1 } ) )
	
  def doTicket( self, command, formName="DUNGEONTICKET", param=None, extraForms=None, start=None, length=None ):
    
    dacform = { 'name': self.deviceName, 'data': self.dac }
    ticketform = False
    if self.token:
      ticketform = { 'name': self.ticketFormName, 'data': self.token }
    
    commandid = "\x05"
    
    if command in [ "LSMYBACKUPS", "ADDBACKUP", "REMOVEBACKUP", "VIEWCONFIGURATION", "LICENSEINFO", "LOGIN_BY_SSO" ]:
      commandid = "\b"
    
    if command in [ "DELETE", "INFO", "RENAME", "MOVE" ]:
      commandid = "\x06"
      
    if command in [ "LIST", "GET", "PUT" ]:
      requestform = { 'name': formName, 'data' : "AG\x05\x06" }
    else:
      if formName != self.ticketFormName:
	if param == None:
	  requestform = { 'name': formName, 'data' : "AG\x05"+ commandid + "command=" + command + "#;" }
	else:
	  requestform = { 'name': formName, 'data' : "AG\x05"+ commandid + "command=" + command + "#" + param + ";" }
	
    forms = False
    if ticketform:
      if formName != self.ticketFormName:
	forms = [ticketform, dacform, requestform]
      else:
	forms = [ticketform, dacform]
    else:
      if formName != self.ticketFormName:
	forms = [dacform, requestform]
      else:
	forms = [dacform]
      
    if extraForms != None:
      for form in extraForms:
	forms.append(form)
    final = True
    if command == "PUT":
      final = False
    contenttype, formdata, boundary = self.getFormData( forms, final )
    
    #logging.debug(command + ' ' + formdata)
    
    headers = {"User-Agent": self.useragent, "Content-Type" : contenttype, "Accept" : "*/*"}
    connection = httplib.HTTPSConnection(self.server)
    #connection.set_debuglevel(9)
    
    
    if command == 'PUT':
      return connection, boundary, formdata, headers
    
    connection.request("POST", "/gate/dungeongate.php", formdata, headers)
    response = connection.getresponse()
    
    if command == 'GET':
      return connection, response, boundary
    
    data = response.read()
    connection.close()
    if command not in [ "LIST", "GET", "INFO", "RENAME" ]:
      return self.parseMeta(data)
    else:
      return data
  
  def generateMetaList ( self, params ) :
    paramstring = ""
    
    for key,param in params.items():
      first = True
      paramstring+=key+"="
      for item in param:
	if first == False:
	  paramstring += "|"
	else:
	  first = False
	paramstring += str(len(str(item))) + "|" + str(item)
      paramstring+="|#"
    return paramstring
  
  def generateMeta ( self, param, params, param2 = False, params2 = False, param1Name="parameters", param2Name="options" ):
    paramstring = param1Name+"=" + str(len(param)) + "|" + param + "|" + str(len(params[param])) + "|" + params[param] + "|"
    del params[param]
    
    for key in params.keys():
      value = params[key]
      
      paramstring += str(len(key)) + "|"  + key + "|" + str(len( str(value) )) + "|" + str(value) + "|"
    
    if param2:
      paramstring += "#"+ param2Name+"=" + str(len(param2)) + "|" + param2 + "|" + str(len(params2[param2])) + "|" + params2[param2] + "|"
      del params2[param2]
      
      for key in params2.keys():
	value = params2[key]
	
	paramstring += str(len(key)) + "|"  + key + "|" + str(len( str(value) )) + "|" + str(value) + "|"
      
    return paramstring + "#"
    
  def parseMeta( self, metadata ):
    # turn meta from server into nice array
    # metadata, parse
    resultdata = {}
    pos = 0
    responsetype = metadata[ metadata.find("=")+1 : metadata.find("#") ]
    metadata = metadata[ metadata.find("#")+1: len(metadata) ]
    strlen = len( metadata )
    prog = re.compile("(.*?)=(\d+)\|")
    count = 0
    resultdata[count] = {}
    while pos < strlen:
      itemdata = metadata[ pos : len( metadata ) ]
      result = prog.search(itemdata)
      if result != None:
	varname, varlength = result.groups()
	varname = varname[ varname.find("#")+1: len(varname) ]
	varvalue = itemdata[result.end(2)+1 : result.end(2) + 1 + int(varlength)]
	pos += len( result.group(0) ) + int(varlength) + 2
      else:
	# must have hit end
	break
      
      if varname in resultdata[count]:
	count+=1
	resultdata[count] = {}
      
      resultdata[count][varname] = varvalue
    
    if len(resultdata[0]) > 0:
      return responsetype, resultdata
    else:
      return responsetype,metadata
      
      
  def getFormData ( self, forms, finishContent = True ) :
    CRLF = '\r\n'
    formparts = []
    boundary =  mimetools.choose_boundary()
    
    for form in forms:
      formparts.append("------------------------------" + boundary)
      if 'filename' in form:
	formparts.append("Content-Disposition: form-data; name=\"" + form['name'] +"\"; filename=\"" + form['filename'] +"\"")
      else:
	formparts.append("Content-Disposition: form-data; name=\"" + form['name'] +"\"\r\n")
      formparts.append(form['data'])
    
    if finishContent:
      formparts.append("------------------------------" + boundary + "--")
    
    formdata = CRLF.join(formparts)
    
    contenttype = "multipart/form-data; boundary=----------------------------" + boundary
    
    return contenttype, formdata, boundary
