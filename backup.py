#! /usr/bin/python
import httplib, urllib, sys, mimetools,re, os, pickle, time, socket, hashlib, ConfigParser, getopt, mimetypes, datetime, mmap

# setup paths
global tokenexpiry, workstation_id, workstation_name
quickConnect = 1
configdir = ".backup2isp"
tokenfilename = "token"
configpath = os.path.join(os.getenv("HOME"), configdir)
configfile = os.path.join( configpath, "config" )

if not os.path.exists( configpath ):
  os.mkdir( configpath )

config = ConfigParser.ConfigParser()

if not os.path.exists( configfile ):
  # config file doesnt exist, create one with default options, have user fill in blanks
  config.add_section('Version')
  config.set("Version", "version", 1 )
  
  config.add_section('Server')
  config.set('Server', 'useragent', 'AGBackup-VirginMedia-en_EN-v2.3.1.31082-AGBK_VIRGIN_W-Backup n Storage-WIN_Seven-?-DG')
  config.set('Server', 'server', 'cl-virgin.ob.f-secure.com')
  config.set('Server', 'dac', 'AGD44cdx56rtt7u8')
  #config.set('Server', 'provider', raw_input('Your provider [ virgin, steek, f-secure ]:') # only support virgin currently
  config.set('Server', 'provider', 'virgin')
  config.set('Server', 'username', raw_input('Your username:'))
  config.set('Server', 'password', raw_input('Your password:'))
  
  config.add_section('Local')
  config.set('Local', 'localpath', raw_input('Local path to backup:'))
  config.set('Local', 'remotepath', raw_input('Remote destination:'))
  config.set('Local', 'backupname', raw_input('Backup name:'))
  
  
  # Writing our configuration file to 'example.cfg'
  with open(configfile, 'wb') as configdetail:
      config.write(configdetail)
else:
  config.readfp( open(configfile) )

useragent = config.get('Server', 'useragent')
server = config.get('Server', 'server')
dac = config.get('Server', 'dac')
provider = config.get('Server', 'provider')
username = config.get('Server', 'username')
password = config.get('Server', 'password')
backupName = config.get('Local', 'backupname')
remotepath = config.get('Local', 'remotepath')
syncpath = config.get('Local', 'localpaths')[0]

tokenfile = os.path.join(configpath, tokenfilename)


workstation_name = socket.gethostname()
workstation_id = hashlib.md5(workstation_name).hexdigest()

tokenexpiry = 0

def versionCheck ( ):
  headers = {"User-Agent": useragent}
  connection = httplib.HTTPSConnection(server)
  connection.request("GET", "/gate/checkme.php", {}, headers)
  response = connection.getresponse()
  data = ""
  responsedata = response.read()
  if ( responsedata != 'CUR' ):
    data = "Not latest version: " + responsedata
  else:
    data = "Latest version: " + responsedata
  connection.close()
  return data

def ping ( ):
  headers = {"User-Agent": useragent}
  connection = httplib.HTTPSConnection(server)
  connection.request("GET", "/gate/ping.php", {}, headers)
  response = connection.getresponse()
  if ( response.read() ):
    print "Connected"
  else:
    print "Failed to connect"
    connection.close()
    sys.exit()
  connection.close()

# had to implement this myself, as urllib doesnt cope with multiple forms in one post well, and server does silly things
def getFormData ( forms, finishContent = True ) :
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


def authenticate( username, password, backup ):
  global tokenexpiry, token
  token = "unset"
  print "Authenticating"
  
  # check for existing token
  if os.path.exists( tokenfile ):
    print "Checking existing token"
    f = open(tokenfile, "r")
    savedbackup, savedtime, savedtoken = pickle.load(f)
    f.close()
    if backup != savedbackup:
      print "Different backup, getting new auth token"
    else:
      if savedtime >= time.time():
	tokenexpiry = savedtime
	return savedtoken
      else:
	print "Token expired"
  else:
    print "No existing token"
  dacform = { 'name': 'DUNGEONDEVICE', 'data': dac }
  authform = { 'name': 'AYMARA', 'data' : "AG\x05\bcommand=LOGIN_BY_SSO#" + 
  generateMeta( "sso_mode", { 'sso_mode' : "virgin" } , 
		"login", { 'login' : username, 'password' : password, 'backup_name' : backup } ) + "#;" }
  
  forms = [dacform, authform]
  
  contenttype, formdata, boundary = getFormData( forms )
  
  #connection.set_debuglevel(9)
  headers = {"User-Agent": useragent, "Content-Type" : contenttype, "Accept" : "*/*"}
  connection = httplib.HTTPSConnection(server)
  connection.request("POST", "/gate/dungeongate.php", formdata, headers)
  response = connection.getresponse()
  tokendata = response.read()
  connection.close()
  results = parseMeta( tokendata )
  results = results[0]
  if "session" not in results:
    if "label" in results:
      print "Failed to login: " + results["label"]
      if results["label"] == "INVALID_BACKUP_POINT":
	# new backup, create one
	token = authenticate( username, password, '' )
	addBackup( backup )
	return authenticate( username, password, backup )
	
      else:
	return None
    else:
      print "Failed to login, unknown error"
      return None
  tokenexpiry = int(results["duration"]) + int(time.time())
  
  # write token to file with expiry time
  f = open(tokenfile, "w")
  pickle.dump( ( backup, tokenexpiry, results["session"] ) , f)
  f.close()

  
  return results["session"]
  

def doTicket( command , param=None, vault=False ):
  global tokenexpiry, token
  
  # get new auth token if time expired
  if tokenexpiry < time.time():
    token = authenticate( username, password, backupName )
  
  dacform = { 'name': 'DUNGEONDEVICE', 'data': dac }
  ticketform = { 'name': 'DUNGEONTICKET', 'data': token }
  
  commandid = "\x05"
  
  if vault or command in [ "LSMYBACKUPS", "ADDBACKUP", "REMOVEBACKUP", "VIEWCONFIGURATION", "LICENSEINFO" ]:
    commandid = "\b"
  
  
  if command in [ "DELETE" ]:
    commandid = "\x06"
    
  if param == None:
    requestform = { 'name': 'AYMARA', 'data' : "AG\x05"+ commandid +"command=" + command + "#;" }
  else:
    requestform = { 'name': 'AYMARA', 'data' : "AG\x05"+ commandid + "command=" + command + "#" + param + ";" }
    
  
  forms = [ticketform, dacform, requestform]
  
  contenttype, formdata, boundary = getFormData( forms )
  
  
  headers = {"User-Agent": useragent, "Content-Type" : contenttype, "Accept" : "*/*"}
  connection = httplib.HTTPSConnection(server)
  #connection.set_debuglevel(9)
  connection.request("POST", "/gate/dungeongate.php", formdata, headers)
  response = connection.getresponse()
  data = response.read()
  connection.close()
  return parseMeta(data)

if not quickConnect:
  # check for new version, we dont care about the result , but need to do this to look like a "real" client
  versionCheck()

  # ping, again its pointless, but real client does this, so we will too
  ping()
#else:
#  print "Quick connecting, skipping useless stuff"
  

def parseMeta( metadata ):
  # turn meta from server into nice array
  # metadata, parse
  resultdata = {}
  pos = 0
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
    return resultdata
  else:
    return metadata

def listBackups():
  return doTicket("LSMYBACKUPS")
  
def listBackup():
  return doTicket("LSBACKUP")[0]
  
def generateMeta ( param, params, param2 = False, params2 = False ):
  paramstring = "parameters=" + str(len(param)) + "|" + param + "|" + str(len(params[param])) + "|" + params[param] + "|"
  del params[param]
  
  for key in params.keys():
    value = params[key]
    
    paramstring += str(len(key)) + "|"  + key + "|" + str(len( str(value) )) + "|" + str(value) + "|"
  
  if param2:
    paramstring += "#options=" + str(len(param2)) + "|" + param2 + "|" + str(len(params2[param2])) + "|" + params2[param2] + "|"
    del params2[param2]
    
    for key in params2.keys():
      value = params2[key]
      
      paramstring += str(len(key)) + "|"  + key + "|" + str(len( str(value) )) + "|" + str(value) + "|"
    
  return paramstring + "#"
  
def addBackup( name ):
  global workstation_id, workstation_name
  return doTicket("ADDBACKUP", generateMeta( "backup_name", { "backup_name" : name,
					       "workstation_id" : workstation_id, 
					       "workstation_name" : workstation_name } , 
					       "session_name", 
					       { "session_name" : "user",
					       "notification" : 1 } ) )

def deleteBackup( name ):
  global workstation_id, workstation_name
  return doTicket("REMOVEBACKUP", generateMeta( "backup_name", { "backup_name" : name,
					       "workstation_id" : workstation_id, 
					       "workstation_name" : workstation_name } , 
					       "session_name", 
					       { "session_name" : "user",
					       "notification" : 1 } ) )

def uploadMultipleFiles ( localpath, remotepath="/" ):
  if os.path.isfile(localpath):
    uploadFile( localpath, remotepath )
  else:
    for root, dirs, files in os.walk(localpath):
      for name in files:
	  remotedest = root.replace( localpath, "" )
	  destdir = (remotepath + remotedest).replace("//", "/")
	  
	  #print "Uploading", os.path.join(root, name), "to", destdir
	  uploadFile( os.path.join(root, name), destdir )
	  #print "Done"
  return True

def uploadFile ( filepath, path="/" ) :
  #deleteFileByPath(filepath, path)
  global tokenexpiry, token
  print "Uploading" , filepath, "to", path
  
  try:
    contenttypetextdetail = mimetypes.guess_type( filepath )
    contenttypetext = "text/plain"
    if contenttypetextdetail[0] != None:
      contenttypetext = contenttypetextdetail[0]
    
    filename = os.path.basename(filepath)
    filehandle = open(filepath)
    
    sha1hash = hashlib.sha1();
    while True:
      buf = filehandle.read(0x100000)
      if not buf:
	  break
      sha1hash.update(buf)
    
    sha1 = sha1hash.hexdigest().upper()

    # get new auth token if time expired
    if tokenexpiry < time.time():
      token = authenticate( username, password, backupName )
    
    ticketform = { 'name': 'DUNGEONTICKET', 'data': token }
    dacform = { 'name': 'DUNGEONDEVICE', 'data': dac }
    requestform = { 'name': 'AYMARA', 'data' : "AG\x05\x06" }
    commandform = { 'name': 'command', 'data' : "PUT" }
    init = { 'name': 'init', 'data' : "13000" }
    option1 = { 'name': 'option1', 'data' : "O" }
    option10 = { 'name': 'option10', 'data' : "" }
    timedetail = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(os.path.getmtime(filepath)))
    option2 = { 'name': 'option2', 'data' : timedetail }
    option3 = { 'name': 'option3', 'data' : "15" }
    option4 = { 'name': 'option4', 'data' : "0" }
    option5 = { 'name': 'option5', 'data' : "2|#type=1|0|#hidden=1|0|#system=1|0|#readonly=1|0|#permissions=1|0|#;" }
    option6 = { 'name': 'option6', 'data' : "SHA1:" + sha1 }
    option7 = { 'name': 'option7', 'data' : "NOT_CRYPTED" }
    option8 = { 'name': 'option8', 'data' : "0" }
    option9 = { 'name': 'option9', 'data' : "" }
    param1 = { 'name': 'param1', 'data' : path }
    param2 = { 'name': 'param2', 'data' : filename }
    
    filesize = os.path.getsize(filepath)
    filedetail = { 'name': 'file', 'data' : "Content-Type: " + contenttypetext + "\r\n\r\n", 'filename' : filename }
    forms = [ticketform, dacform,requestform, commandform, init, option1, option10,option2, option3, option4, option5, option6, option7, option8, option9, param1, param2, filedetail]
    
    contenttype, formdata, boundary = getFormData( forms, False )
    
    connection = httplib.HTTPSConnection(server)
    #connection.set_debuglevel(9)
    finalstring = "\r\n------------------------------" + boundary + "--"
    headers = {"User-Agent": useragent, "Content-Type" : contenttype, "Accept" : "*/*", "Content-Length": len( formdata ) + filesize + len(finalstring) }
    connection.putrequest("POST", "/gate/dungeongate.php")
    for item in headers.keys():
      connection.putheader( item, headers[item] )
    connection.endheaders()
    connection.send(formdata)
    
    filehandle.seek(0)
    while True:
      buf = filehandle.read(0x100000)
      if not buf:
	  break
      connection.send( buf )
    
    connection.send(finalstring)
    
    response = connection.getresponse()
    responsedata = response.read()
    connection.close()
    print "Uploaded" , filepath, "to", path
    return responsedata
  except Exception as error:
    print "Error:",error
  filehandle.close()
  return False



def deleteFiles ( ids ):
  details = "ids="
  detail2 = "|#types="
  first = True
  for id in ids:
    if first == False:
      details += "|"
    else:
      first = False
    if id[0] == "AG\x05\x05F":
      id[0] = "F"
    if id[0] == "AG\x05\x05D":
      id[0] = "D"
    details += str(len(str(id[6]))) + "|" + str(id[6])
    detail2 += str(len(id[0])) + "|"+ id[0] + "|"
  fullcommand = details + detail2 + '#'
  print fullcommand
  return doTicket("DELETE", fullcommand)

def deleteFileByPath ( filepath, path="/" ):
  print "Deleting ", filepath, "from", path
  files = listFiles(path)
  # no files, abort
  if len(files) <= 0:
    print "No files in path"
    return False
  fileids = []
  for filedetail in files:
    if len(filedetail) > 1:
      if ( filedetail[0].find("INVALID_FOLDER") == -1 ) and ( filedetail[1] in filepath ) or ( filepath[0] == "*" ):
	fileids.append( filedetail )
	if filedetail[0] == "D":
	  deleteFileByPath("*"  , path + "/" + filedetail[1] )
  if len( fileids ) > 0:
    return deleteFiles( fileids )
  else:
    print "Nothing matching name to delete"
    return False
  
def listFiles ( path="/" ):
  global tokenexpiry, token
  
  # get new auth token if time expired
  if tokenexpiry < time.time():
    token = authenticate( username, password, backupName )
  
  dacform = { 'name': 'DUNGEONDEVICE', 'data': dac }
  ticketform = { 'name': 'DUNGEONTICKET', 'data': token }
  requestform = { 'name': 'AYMARA', 'data' : "AG\x05\x06" }
  
  commandform = { 'name': 'command', 'data' : "LIST" }
  initform = { 'name': 'init', 'data' : "13000" }
  option1 = { 'name': 'option1', 'data' : "" }
  option2 = { 'name': 'option2', 'data' : "" }
  param1 = { 'name': 'param1', 'data' : path }
  
  forms = [ticketform, commandform, dacform, requestform, initform, option1, option2, param1]
  
  contenttype, formdata, boundary = getFormData( forms )
  
  #connection.set_debuglevel(9)
  headers = {"User-Agent": useragent, "Content-Type" : contenttype, "Accept" : "*/*"}
  connection = httplib.HTTPSConnection(server)
  connection.request("POST", "/gate/dungeongate.php", formdata, headers)
  response = connection.getresponse()
  filelist = response.read()
  connection.close()
  details = []
  for line in filelist.splitlines():
    details.append( line.split("|") )
  return details

def getFile ( path, destfile,modtime=None ):
  global tokenexpiry, token
  
  # get new auth token if time expired
  if tokenexpiry < time.time():
    token = authenticate( username, password, backupName )
    
  # if its a dir, recurse through tree and get all
  details = listFiles(path)
  if len(details[0]) > 1:
    # is a dir
    if not os.path.exists(destfile):
      os.makedirs(destfile)
    for detail in details:
      # convert time supplied to unix time
      timestamp = datetime.datetime.strptime(detail[4], "%Y-%m-%d %H:%M:%S")
      modtime = timestamp.strftime("%s")
    
      getFile(os.path.join(path,detail[1]), os.path.join(destfile, detail[1]), int(modtime))
    return
    
  if modtime == None:
    # fetch modification time, need to file dirname
    itemname = os.path.basename(path)
    dirname = os.path.dirname(path)
    if dirname == "":
      dirname = "/"
    filelist = listFiles(dirname)
    for filedetail in filelist:
      if filedetail[1] == itemname:
	timestamp = datetime.datetime.strptime(filedetail[4], "%Y-%m-%d %H:%M:%S")
	modtime = int(timestamp.strftime("%s"))
	
  print "Putting", path, "to",destfile
  dacform = { 'name': 'DUNGEONDEVICE', 'data': dac }
  ticketform = { 'name': 'DUNGEONTICKET', 'data': token }
  requestform = { 'name': 'AYMARA', 'data' : "AG\x05\x06" }
  
  filename = os.path.basename(path)
  path = os.path.dirname(path)
  
  commandform = { 'name': 'command', 'data' : "GET" }
  initform = { 'name': 'init', 'data' : "13000" }
  param1 = { 'name': 'param1', 'data' : path }
  param2 = { 'name': 'param2', 'data' : filename }
  
  forms = [ticketform, commandform, dacform, requestform, initform, param1, param2]
  
  contenttype, formdata, boundary = getFormData( forms )
  
  
  #connection.set_debuglevel(9)
  headers = {"User-Agent": useragent, "Content-Type" : contenttype, "Accept" : "*/*"}
  connection = httplib.HTTPSConnection(server)
  connection.request("POST", "/gate/dungeongate.php", formdata, headers)
  response = connection.getresponse()

  writefile = None
  while True:
    buf = response.read(0x10000)
    if buf[0:5] == "ERROR":
        return False
    if not buf:
	break
    if writefile == None:
      writefile = open(destfile,"w")
    writefile.write( buf )
  
  writefile.close()
  os.utime(destfile,(time.time(), modtime))
  
  connection.close()
    
  return True

def listFileTreeRemote(path, originalpath):
  fulllist = dict()
  details = listFiles(path)
  if len(details[0]) > 1:
    for detail in details:
      if detail[0] == "F" or detail[0] == "AG\x05\x05F":
	rawpath = os.path.join(path, detail[1])
	filepath = rawpath[len(originalpath):len(rawpath)]
	itemdetails = {"filesize": int(detail[2]), "modified" : detail[4]}
	fulllist[filepath] = itemdetails
      else:
	subitems = listFileTreeRemote(os.path.join(path, detail[1]), originalpath)
	for subitemkey in subitems.keys():
	  subitem = subitems[subitemkey]
	  fulllist[subitemkey] = subitem
  return fulllist
  
def listFileTreeLocal(localpath):
  fulllist = dict()
  for root, dirs, files in os.walk(localpath):
    for name in files:
        rawpath = os.path.join(root, name)
	filepath = rawpath[len(localpath):len(rawpath)]
	size = os.path.getsize(rawpath)
	itemdetails = {"path" : rawpath,"filesize" : size, "modified" : time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(os.path.getmtime(rawpath)))}
	fulllist[filepath] = itemdetails
  return fulllist

def sync ( localpath, path="/" ) :
  print "Finding remote items"
  remoteitems = listFileTreeRemote(path, path)
  
  print "Finding local items"
  localitems = listFileTreeLocal(localpath)
  diffitems = dict()
  
  # compare and upload different
  
  for key in localitems:
    localitem = localitems[key]
    if key in remoteitems:
      remoteitem = remoteitems[key]
      if remoteitem["filesize"] != localitem["filesize"] or remoteitem["modified"] != localitem["modified"]:
	diffitems[key] = localitem
    else:
      diffitems[key] = localitem
  
  for key in diffitems:
    item = diffitems[key]
    remotedest = item["path"].replace( localpath, "" )
    destdir = (path + remotedest).replace("//", "/")
    uploadFile(item["path"], os.path.dirname(destdir))
  if len(diffitems) == 0:
    print "Nothing to sync"
    
if __name__ == '__main__':
    import getopt
    
    opts, args = getopt.getopt(sys.argv[1:], "help")
    if len(args) == 0:
      print "Use one of these commands: upload delete list download"
      sys.exit(2)
    
    if args[0] == "versioncheck":
	print versionCheck()
	sys.exit(0)

    if args[0] == "viewconfiguration":
	print doTicket("VIEWCONFIGURATION")
	sys.exit(0)

    if args[0] == "licenseinfo":
	print doTicket("LICENSEINFO")
	sys.exit(0)
      
    if args[0] == "upload":
      if len(args) < 2:
	print "You must supply a path to upload"
	sys.exit(2)
      else:
	if not os.path.exists( args[1] ):
	  print "File does not exist"
	  sys.exit(2)
	else:
	  if len(args) > 1:
	    args.append("/")
	  uploadMultipleFiles(args[1], args[2])
	  sys.exit(0)
    
    if args[0] == "delete":
      path = "/"
      filename = args[1]
      if len(args) == 3:
	path = args[2]
      path = os.path.dirname(filename)
      if len(path) == 0:
	path = "/"
      filename = os.path.basename(filename)
      deleteFileByPath( filename, path )
      sys.exit(0)
      
      
    if args[0] == "listbackups":
      print listBackups()
      sys.exit(0)
      
    if args[0] == "list":
      path = "/"
      if len(args) > 1:
	path = args[1]
      files = listFiles(path)
      for file in files:
	if len(file) == 1:
	  print file
	else: 
	  print file[1], " - ", file[0] , "-",file
      sys.exit(0)
	  
    if args[0] == "download":
      destpath = os.path.basename( args[1] )
      if len(args) > 2:
	destpath = args[2]
      if getFile(args[1], destpath):
	print "Written file to", destpath
	sys.exit(0)
      else:
	print "Unable to fetch file"
	sys.exit(1)
	
    if args[0] == "createbackup":
      backupname = args[1]
      print addBackup(backupname)
      sys.exit(0)
      
    if args[0] == "deletebackup":
      backupname = args[1]
      print deleteBackup(backupname)
      sys.exit(0)
      
      
    if args[0] == "sync":
      sync(args[1], args[2])
      sys.exit(1)
      
    if args[0] == "rawcommand":
      if len(args) > 2 and args[2] == "1":
	print doTicket(args[1], None, True)
      else:
	print doTicket(args[1], None, False)
      sys.exit(0)
      
    print "No commands entered"
