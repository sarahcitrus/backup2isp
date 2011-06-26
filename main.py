#! /usr/bin/python
import httplib, urllib, sys, mimetools,re, os, pickle, time, socket, hashlib, ConfigParser, getopt

# setup paths
global tokenexpiry, workstation_id, workstation_name
quickConnect = 1
backupName = "testbackup"
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

tokenfile = os.path.join(configpath, tokenfilename)


workstation_name = socket.gethostname()
workstation_id = hashlib.md5(workstation_name).hexdigest()

tokenexpiry = 0

connection = httplib.HTTPSConnection(server)

def versionCheck ( ):
  headers = {"User-Agent": useragent}
  connection.request("GET", "/gate/checkme.php", {}, headers)
  response = connection.getresponse()
  if ( response.read() != 'CUR' ):
    print "Server says we are not running latest version"
  else:
    print "Latest version useragent"

def ping ( ):
  headers = {"User-Agent": useragent}
  connection.request("GET", "/gate/ping.php", {}, headers)
  response = connection.getresponse()
  if ( response.read() ):
    print "Connected"
  else:
    print "Failed to connect"
    sys.exit()

# had to implement this myself, as urllib doesnt cope with multiple forms in one post well, and server does silly things
def getFormData ( forms ) :
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
   
  formparts.append("------------------------------" + boundary + "--")
  
  formdata = CRLF.join(formparts)
   
  contenttype = "multipart/form-data; boundary=----------------------------" + boundary
   
  return contenttype, formdata


def authenticate( username, password, backup ):
  global tokenexpiry, token
  
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
  generateMeta( "sso_mode", { 'sso_mode' : provider } , 
		"login", { 'login' : username, 'password' : password, 'backup_name' : backup } ) + "#;" }
  
  forms = [dacform, authform]
  
  contenttype, formdata = getFormData( forms )
  
  #connection.set_debuglevel(9)
  headers = {"User-Agent": useragent, "Content-Type" : contenttype, "Accept" : "*/*"}
  connection.request("POST", "/gate/dungeongate.php", formdata, headers)
  response = connection.getresponse()
  tokendata = response.read()
  results = parseMeta( tokendata )
  results = results[0]
  if "session" not in results:
    if "label" in results:
      print "Failed to login: " + results["label"]
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
  

def doTicket( command , param=None ):
  global tokenexpiry, token
  
  # get new auth token if time expired
  if tokenexpiry < time.time():
    token = authenticate( username, password, backupName )
  
  dacform = { 'name': 'DUNGEONDEVICE', 'data': dac }
  ticketform = { 'name': 'DUNGEONTICKET', 'data': token }
  if param == None:
    requestform = { 'name': 'AYMARA', 'data' : "AG\x05\x06command=" + command + "#;" }
  else:
    requestform = { 'name': 'AYMARA', 'data' : "AG\x05\x06command=" + command + "#" + param + ";" }
    
  
  forms = [ticketform, dacform, requestform]
  
  contenttype, formdata = getFormData( forms )
  
  #connection.set_debuglevel(9)
  headers = {"User-Agent": useragent, "Content-Type" : contenttype, "Accept" : "*/*"}
  connection.request("POST", "/gate/dungeongate.php", formdata, headers)
  response = connection.getresponse()
  print response.read()
  return parseMeta(response.read())

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
      
  return resultdata

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

def uploadMultipleFiles ( localpath, remotepath="/" ):
  if os.path.isfile(localpath):
    uploadFile( localpath, remotepath )
  else:
    for root, dirs, files in os.walk(localpath):
      for name in files:
	  remotedest = root.replace( localpath, "" )
	  destdir = (remotepath + remotedest).replace("//", "/")
	  
	  print "Uploading", os.path.join(root, name), "to", destdir
	  uploadFile( os.path.join(root, name), destdir )
	  print "Done"
  return True

def uploadFile ( filepath, path="/" ) :
  #deleteFileByPath(filepath, path)
  global tokenexpiry, token
  
  filename = os.path.basename(filepath)
  filehandle = open(filepath)
  filecontents = filehandle.read()
  sha1 = hashlib.sha1( filecontents ).hexdigest().upper()

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
  option2 = { 'name': 'option2', 'data' : time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(os.path.getmtime(filepath))) }
  option3 = { 'name': 'option3', 'data' : "15" }
  option4 = { 'name': 'option4', 'data' : "0" }
  option5 = { 'name': 'option5', 'data' : "2|#type=1|0|#hidden=1|0|#system=1|0|#readonly=1|0|#permissions=1|0|#;" }
  option6 = { 'name': 'option6', 'data' : "SHA1:" + sha1 }
  option7 = { 'name': 'option7', 'data' : "NOT_CRYPTED" }
  option8 = { 'name': 'option8', 'data' : "0" }
  option9 = { 'name': 'option9', 'data' : "" }
  param1 = { 'name': 'param1', 'data' : path }
  param2 = { 'name': 'param2', 'data' : filename }
  filedetail = { 'name': 'file', 'data' : "Content-Type: text/plain\r\n\r\n" + filecontents , 'filename' : filename }
  
  forms = [ticketform, dacform,requestform, commandform, init, option1, option10,option2, option3, option4, option5, option6, option7, option8, option9, param1, param2, filedetail]
  
  contenttype, formdata = getFormData( forms )
  
  #connection.set_debuglevel(9)
  headers = {"User-Agent": useragent, "Content-Type" : contenttype, "Accept" : "*/*"}
  print "Uploading" , filepath, "to", path
  connection.request("POST", "/gate/dungeongate.php", formdata, headers)
  response = connection.getresponse()
  print "Uploaded" , filepath, "to", path
  filehandle.close()
  return response.read()




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
    details += str(len(str(id[6]))) + "|" + str(id[6])
    detail2 += str(len(id[0])) + "|"+ id[0] + "|"
  fullcommand = details + detail2 + '#'
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
  
  contenttype, formdata = getFormData( forms )
  
  #connection.set_debuglevel(9)
  headers = {"User-Agent": useragent, "Content-Type" : contenttype, "Accept" : "*/*"}
  connection.request("POST", "/gate/dungeongate.php", formdata, headers)
  response = connection.getresponse()
  filelist = response.read()
  details = []
  for line in filelist.splitlines():
    details.append( line.split("|") )
  return details

def getFile ( path, destfile ):
  global tokenexpiry, token
  
  # get new auth token if time expired
  if tokenexpiry < time.time():
    token = authenticate( username, password, backupName )
  
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
  
  contenttype, formdata = getFormData( forms )
  
  
  #connection.set_debuglevel(9)
  headers = {"User-Agent": useragent, "Content-Type" : contenttype, "Accept" : "*/*"}
  connection.request("POST", "/gate/dungeongate.php", formdata, headers)
  response = connection.getresponse()
  
  writefile = open(destfile,"w")
  print "got response"
  writefile.write( response.read() )
  print "written"
  writefile.close()
  
  return True
  

if __name__ == '__main__':
    import getopt
    
    opts, args = getopt.getopt(sys.argv[1:], "help")
    if len(args) == 0:
      print "Use one of these commands: upload delete list get"
      sys.exit(2)
      
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
      
    if args[0] == "list":
      path = "/"
      if len(args) > 1:
	path = args[1]
      files = listFiles(path)
      for file in files:
	if len(file) == 1:
	  print file
	else: 
	  print file[1], " - ", file[0]
	  
    if args[0] == "get":
      print getFile(args[1], args[2])
    #print "Logging in"

    #token = authenticate( username, password, backupName)
    #if token == None:
    #  print "Login failed"
    #  sys.exit(1)
    #print "Auth expires ", time.ctime(tokenexpiry)

    #if not quickConnect:
      # again, gives us info we dont care about, but if not on quick mode dont do it
      #listBackups()
      #doTicket("VIEWCONFIGURATION")


    #print doTicket("LIST")
    #print listBackup()
    #print uploadMultipleFiles("/local/files", "/Pictures/test123")
    #print deleteFileByPath( ["test2"], "/Pictures/test12" )
    #doTicket("GETTIMESTAMP");