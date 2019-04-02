# coding: utf-8

import traceback
import copy

from appPublic.jsonConfig import getConfig
from appPublic.folderUtils import endsWith
from appPublic.rsa import RSA
from WebServer.globalEnv import UserNeedLogin,WebsiteSessiones

from vibora.request import Request
from vibora.static import StaticHandler
from vibora.exceptions import StaticNotFound

class NotImplementYet(Exception):
    pass

class RefusedResource(StaticHandler):
	async def handle(self,request:Request):
		path = self.extract_path(request)
		return path + b':refused access!'

class UnknownException(Resource):
	def __init__(self,e,*args,**kwargs):
		super(UnknownException,self).__init__(*args,**kwargs)
		self.e = e
		
	def handle(self,request:Request):
		path = self.extract_path(request)
		print('Exception.....!',path,'exception=',self.e,'type e=',type(self.e))
		return path + b':exception happend'
		
class ACBase:
	"""
	网站访问控制基本类
	需要继承此类，并实现checkPassword，和checkUserPrivilege两个函数
	使用例子：
	class MyAC(ACBase):
		def checkPassword(self,user,password):
			myusers= {
				'root':'pwd123'
				'user1':'pwd123'
			}
			p = myusers.get(user,None)
			if p == None:
				return False
			if p != password:
				return False
			return True
		def checkUserPrivilege(self,user,path):
			# 用户可以做任何操作
			return True
		
	在需要控制的地方
	ac = MyAC()
	if not ac.accessCheck(request):
		#拒绝操作
	# 正常操作
	"""
	def __init__(self):
		self.conf = getConfig()
		self.rsaEngine = RSA()
		fname = self.conf.website.rsakey.privatekey
		self.privatekey = self.rsaEngine.read_privatekey(fname,'ymq123')
		
	def _selectParseHeader(self,authheader):
		txt = self.rsaEngine.decode(self.privatekey,authheader)
		return txt.split(':')
		
	def checkUserPrivilege(self,user,path):
		raise NotImplementYet

	def checkPassword(self,user,password):
		raise NotImplementYet
		
	def getRequestUserPassword(self,request):
		try:
			authheader = request.getHeader(b'authorization')
			if authheader is not None:
				return self._selectParseHeader(authheader)
			return None,None
		except Exception as e:
			return 'Anonymous',None

	def isNeedLogin(self,path):
		raise NotImplementYet
		
	def acCheck(self,request):
		path = self.extract_path(request)
		ws = WebsiteSessiones()
		user =  ws.getUserid(request)
		if user == None:
			user,password = self.getRequestUserPassword(request)
			if user is None:
				raise UserNeedLogin(path)
			if not self.checkPassword(user,password):
				raise UserNeedLogin(path)
			ws.login(request,user)
	
		if not self.checkUserPrivilege(user,path):
			raise UnauthorityResource()
		return True
		
	def accessCheck(self,request):
		"""
		检查用户是否由权限访问此url
		"""
		path = self.extract_path(request)
		if self.isNeedLogin(path):
			# print('need login')
			return self.acCheck(request)
		#没在配置文件设定的路径不做控制，可以随意访问
		# print('not need login')
		return True
        
class BaseResource(StaticHandler):
	def __init__(self,path,accessController=None):
		super(BaseResource,self).__init__(paths=[path],url_prefix='')
		self.processors = {}
		self.access_controller = accessController

	def endsWith(self,f,s):
		f = f.encode('utf-8') if hasattr(f,'encode') else f
		s = s.encode('utf-8') if hasattr(f,'encode') else s
		return endsWith(f.lower(),s.lower())

	def add_processor(self,id,Klass):
		self.processors[id] = Klass

	async def _handle(self,request:Request):
		path = self.extract_path(request)
		for root_path in self.paths:
			real_path = root_path + path
			if self.exists(real_path):
				for k in self.processors.keys():
					if self.endsWith(path,k):
						h = self.processors[k](path)
						return h.handle(request)
				return super(BaseResource,self).handle(reqest)
		return raise StaticNotFound()
		
	async def handle(self,request:Request):
		if self.access_controller is None:
			return self._handle(request)

		if self.access_controller.accessCheck(request):
			return self._handle(request)

		raise UserNeedLogin
