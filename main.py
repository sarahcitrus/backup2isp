#! /usr/bin/python
import httplib, urllib, sys, mimetools,re, os, pickle, time, socket, hashlib

global tokenexpiry, workstation_id, workstation_name
quickConnect = 1
backupName = "testbackup"
configdir = ".backup2isp"
tokenfilename = "token"

workstation_name = socket.gethostname()
workstation_id = hashlib.md5(workstation_name).hexdigest()


if not os.path.exists( os.path.join(os.getenv("HOME"), configdir) ):
  os.mkdir( os.path.join(os.getenv("HOME"), configdir) )

tokenfile = os.path.join(os.getenv("HOME"), configdir, tokenfilename)

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
    requestform = { 'name': 'AYMARA', 'data' : "AG\x05\bcommand=" + command + "#;" }
  else:
    requestform = { 'name': 'AYMARA', 'data' : "AG\x05\x06command=" + command + "#" + param + ";" }
    
  
  forms = [ticketform, dacform, requestform]
  
  contenttype, formdata = getFormData( forms )
  
  #connection.set_debuglevel(9)
  headers = {"User-Agent": useragent, "Content-Type" : contenttype, "Accept" : "*/*"}
  connection.request("POST", "/gate/dungeongate.php", formdata, headers)
  response = connection.getresponse()
  print  response.read()
  return parseMeta(response.read())

if not quickConnect:
  # check for new version, we dont care about the result , but need to do this to look like a "real" client
  versionCheck()

  # ping, again its pointless, but real client does this, so we will too
  ping()
else:
  print "Quick connecting, skipping useless stuff"
  

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
  
def generateMeta ( param, params, param2, params2 ):
  paramstring = "parameters=" + str(len(param)) + "|" + param + "|" + str(len(params[param])) + "|" + params[param] + "|"
  del params[param]
  
  for key in params.keys():
    value = params[key]
    
    paramstring += str(len(key)) + "|"  + key + "|" + str(len( str(value) )) + "|" + str(value) + "|"
  
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

def uploadMultipleFiles ( localpath, remotepath ):
  for root, dirs, files in os.walk(localpath):
   for name in files:
       destdir = remotepath + root.replace( localpath, "" )
       
       print "Uploading", os.path.join(root, name), "to", destdir
       uploadFile( os.path.join(root, name), destdir )
       print "Done"
  return True

def uploadFile ( filepath, path="/" ) :
  deleteFileByPath(filepath, path)
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
  requestform = { 'name': 'AYMARA', 'data' : "AG\x05\a" }
  commandform = { 'name': 'command', 'data' : "PUT" }
  init = { 'name': 'init', 'data' : "13000" }
  option1 = { 'name': 'option1', 'data' : "0" }
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
  connection.request("POST", "/gate/dungeongate.php", formdata, headers)
  response = connection.getresponse()
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
    details += str(len(str(id))) + "|" + str(id)
    detail2 += "1|F|"
  fullcommand = details + detail2 + '#'
  return doTicket("DELETE", fullcommand)

def deleteFileByPath ( filepath, path="/" ):
  files = listFiles(path)
  # no files, abort
  if len(files) <= 0:
    return False
  fileids = []
  for filedetail in files:
    if filedetail[1] in filepath or filepath[0] == "*":
      fileids.append( filedetail[6] )
  if len( fileids ) > 0:
    return deleteFiles( fileids )
  else:
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

print "Logging in"

token = authenticate( username, password, backupName)
if token == None:
  print "Login failed"
  sys.exit(1)
print "Auth expires ", time.ctime(tokenexpiry)

if not quickConnect:
  # again, gives us info we dont care about, but if not on quick mode dont do it
  listBackups()
  doTicket("VIEWCONFIGURATION")


#print doTicket("LIST")
#print listBackup()
#print uploadMultipleFiles("/mnt/sata4/Completed/Paris/test1", "/Pictures/testdir2")
#print deleteFileByPath( ["test2"], "/Pictures/Paris" )
#doTicket("GETTIMESTAMP");