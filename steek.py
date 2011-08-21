import httplib, urllib, mimetools, re 

class Steek:
  
  tokenexpiry = False
  token = False
  loginFormName = "AYMARA"
  ticketFormName = "DUNGEONTICKET"
  deviceName = 'DUNGEONDEVICE'
  provider = 'virgin'
  server = 'cl-virgin.ob.f-secure.com'
  dac = 'AGD44cdx56rtt7u8'
  useragent = 'AGBackup-VirginMedia-en_EN-v2.3.1.31082-AGBK_VIRGIN_W-Backup n Storage-WIN_Seven-?-DG'

  def login ( self, username, password ) :
    meta = self.generateMeta( "sso_mode", { 'sso_mode' : self.provider } , 
		"login", { 'login' : username, 'password' : password } ) + "#"
    return self.doTicket( self.loginFormName, "LOGIN_BY_SSO", meta )
    
    
    
  def doTicket( self, formName, command , param=None ):
    
    dacform = { 'name': self.deviceName, 'data': self.dac }
    ticketform = False
    if self.token:
      ticketform = { 'name': formName, 'data': self.token }
    
    commandid = "\x05"
    
    if command in [ "LSMYBACKUPS", "ADDBACKUP", "REMOVEBACKUP", "VIEWCONFIGURATION", "LICENSEINFO", "LOGIN_BY_SSO" ]:
      commandid = "\b"
    
    if command in [ "DELETE" ]:
      commandid = "\x06"
      
    if param == None:
      requestform = { 'name': formName, 'data' : "AG\x05"+ commandid +"command=" + command + "#;" }
    else:
      requestform = { 'name': formName, 'data' : "AG\x05"+ commandid + "command=" + command + "#" + param + ";" }
    
    forms = False
    if ticketform:
      forms = [ticketform, dacform, requestform]
    else:
      forms = [dacform, requestform]
    
    contenttype, formdata, boundary = self.getFormData( forms )
    
    
    headers = {"User-Agent": self.useragent, "Content-Type" : contenttype, "Accept" : "*/*"}
    connection = httplib.HTTPSConnection(self.server)
    #connection.set_debuglevel(9)
    connection.request("POST", "/gate/dungeongate.php", formdata, headers)
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return self.parseMeta(data)
    
  def generateMeta ( self, param, params, param2 = False, params2 = False ):
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
