import requests
import json
import datetime
import os
import logging
from O365 import Account, FileSystemTokenBackend
from pathlib import Path

style = '''<style>table {width:880px; border: 1px; border-collapse: collapse; table-layout: fixed;} td {border: 1px solid black; max-width:200px; overflow: hidden; text-overflow: ellipsis; } tr:nth-child(even) {background: #CCC; border: 1px;} tr:nth-child(odd) {background: #FFF; border: 1px;}</style>'''

class AGOL_Manager(object):

	def __init__(self, admin_user, password, url):		

		self.adminuser = admin_user
		#self.password = parser['AGOL']['PASS']
		self._url = url  #https://www.arcgis.com
		self.payload = {'f': 'json', }
		self.token = self.gen_token(self.adminuser, password, self._url)
		if self.token:
			self.payload['token'] = self.token

		self.org_id, self.urlKey, self.base_url, self.org_info, self.admins = self.get_portal_info(self._url)		
		self.url = "https://{}.{}".format(self.urlKey, self.base_url)

		self.geocode_credits = self.geocode(self.url)
		self.geoenrich_credits = self.geoenrich(self.url)
		self.spatialanalysis_credits = self.spatialanalysis(self.url)
		self.users = self.get_users(self.url)

		self._fs = self.list_fs(self.url)
		self.itms = ItemsManager(self._fs).itms

	def _req_resp(self, url, payload):

		response = requests.post(url, data = payload)
		r = json.loads(response.text)

		if response.status_code == 200:			
			if 'error' in r:
				logging.critical("Sent request, but found an error: {err}".format(err=r['error']))
				raise Exception("Sent request, but found an error: {err}".format(err=r['error']))		
		else:
			logging.critical("Error: {err}".format(err=r['error']))
			raise Exception("Error: {err}".format(err=r['error']))

		return r

	def gen_token(self, username, password, url):

		payload = {'username': username,
					'password': password,
					'referer': 'http://www.foo.com',
					'expiration': 30
					}
		p = {**payload, **self.payload}
		url += "/sharing/rest/generateToken"

		res = self._req_resp(url, p)

		return res['token']

	def get_portal_info(self, url):
		url += "/sharing/rest/portals/self"
		res = self._req_resp(url, self.payload)
		
		return res['id'], res['urlKey'], res['customBaseUrl'], res['subscriptionInfo'], res['mfaAdmins']

	def get_users(self, url):
		# 'https://[urlKey].maps.arcgis.com/sharing/rest/portals/self/users'

		u = []
		url += "/sharing/rest/portals/self/users"
		payload = {	'start': 1,
					'num':50
					}
		p = {**payload, **self.payload}
		res = self._req_resp(url, p)

		if len(res['users']) > 0:
			u += res['users']
		
		while res['nextStart'] != -1:
			p['start'] = res['nextStart']
			res = self._req_resp(url, p)
			u += res['users']
			if res['nextStart'] == -1:
				return u
		return u

	def list_fs(self, url):		
		
		url += "/sharing/rest/content/portals/" + self.org_id
		payload = {'num': 50,
					'start':1,
					'sortField': 'size',
					'sortOrder': 'desc',
					'types': 'Feature Service',
					'reservedTypeKeyword': 'Hosted Service'
					}
		p = {**payload, **self.payload}   
		res = self._req_resp(url, p)

		fs =[]
		if len(res['items']) > 0:
			fs += res['items']
		
		while res['nextStart'] != -1:
			p['start'] = res['nextStart']
			res = self._req_resp(url, p)
			fs += res['items']
			if res['nextStart'] == -1:
				return fs
		return fs
		def geocode(self, url):
		
		url += "/sharing/rest/portals/" + self.org_id + "/usage"
		payload = {'stype': "geocode",
					'etype': 'geocodecnt',
					'vars': 'credits,num,stg',
					'period': '7d',
					'startTime': int(time.time() - 60480) * 1000,
					'endTime': int(time.time()) * 1000
					}


		p = {**payload, **self.payload}			
   
		res = self._req_resp(url, p)
		geo_c = {}
		if 'data' in res:
			for d in res['data']:
				cred = 0
				for c in d['credits']:
					cred += float(c[1])
				if d['username'] in geo_c:
					geo_c[d['username']] += cred
				else:
					geo_c[d['username']] = cred
		return geo_c

	def geoenrich(self, url):

		#geoenrich
		#https://esrica-ncr.maps.arcgis.com/sharing/rest/portals/vY6WuhLW0HkFe6Fl/usage?f=json&startTime=1585267200000&endTime=1586526289000&stype=geoenrich&etype=svcusg&vars=credits%2Cnum%2Cstg&period=1d&groupby=username%2Cstype%2Cetype%2Ctask%2Ccredits&token=Orp6vqYqXe0BX9Bb3aj0WV1wOGZbngeSwGy5WGqAtf4bD4ZBORG3D5_TP4x-e33V0116wmrIfRQLoJfluLe2J5SPdfDZMHmBT2SdFq1bKIGTCDKbJFlXi3CxBe0ZOMOPKzEBC5OKhlviUDkxAm3s_ey0gdlSOxytEK-ccdIrlfQ1LUnrUQnVS71Ft9gAoN7OPRRpdngBV-cvpKSwRlbDrARXwoOeAY4fmJKwWii7tfc.
	
		url += "/sharing/rest/portals/" + self.org_id + "/usage"

		payload = {'stype': "geoenrich",
					'etype': 'svcusg',
					'vars': 'credits,num,stg',
					'period': '1w',
					'groupby': 'username,stype,etype,task,credits',
					'startTime': int(time.time() - 60480) * 1000,
					'endTime': int(time.time()) * 1000
					}

		p = {**payload, **self.payload}			
   
		res = self._req_resp(url, p)
		geoenr_c = {}
		if 'data' in res:
			for d in res['data']:
				cred = 0
				for c in d['credits']:
					cred += float(c[1])
				if d['username'] in geoenr_c:
					geoenr_c[d['username']] += cred
				else:
					geoenr_c[d['username']] = cred
		return geoenr_c

	def spatialanalysis(self, url):

		url += "/sharing/rest/portals/" + self.org_id + "/usage"
		payload = {'stype': "spanalysis",
					'etype': 'svcusg',
					'vars': 'credits,num,stg',
					'period': '1w',
					'groupby': 'username,stype,etype,task,credits',
					'startTime': int(time.time() - 60480) * 1000,
					'endTime': int(time.time()) * 1000
					}

		p = {**payload, **self.payload}			
   
		res = self._req_resp(url, p)
		sptanl_c = {}
		if 'data' in res:
			for d in res['data']:
				cred = 0
				for c in d['credits']:
					cred += float(c[1])
				if d['username'] in sptanl_c:
					sptanl_c[d['username']] += cred
				else:
					sptanl_c[d['username']] = cred
		return sptanl_c

def parse_credit(credit_dict):
	out_html = ""
	for k, v in credit_dict.items():
		out_html +="<li>{}: {}".format(k, v)

	return out_html

class ItemsManager(object):

    def __init__(self, fs_list):
        self._users = []
        self._itms = []
        self.parse_load_FS(fs_list)
        self.itms = self.users_items()

    def parse_load_FS(self, fs_list):

        for i in fs_list:
            if i['owner'] not in self._users:
                self._users.append(i['owner'])
            singleItem = {'title': i['title'],
                        'type': i['type'],
                        'url': i['url'],
                        'owner': i['owner'],
                        'numViews': i['numViews'],
                        'access': i['access'],
                        'created': i['created'],
                        'modified': i['modified'],
                        'size': i['size'],
                        'itemID': i['id']
                        }
            self._itms.append(singleItem)
    
    def users_items(self):
        ui = {}
        for u in self._users:
            ui[u] = []
            for i in self._itms:
                if u == i['owner']:
                    ui[u].append(i)                    
        return ui


def nice_date(d):
	return datetime.datetime.fromtimestamp(d/1000).strftime('%Y-%m-%d %H:%M')


def send_o365(api_key, secret, from_email, to_email, email_body, subject):

	credentials = (api_key, secret)
	tokenFile = "o365_token.txt"
	if not os.path.exists(os.path.exists(os.path.join(Path(__file__).parent, tokenFile))):
		logging.critical("o365 emailer cannot find token file. Sending emails will fail.")	

	token_backend = FileSystemTokenBackend(token_path=Path(__file__).parent, token_filename=tokenFile)

	account = Account(credentials, token_backend=token_backend, scopes=['message_send'])
	if not account.authenticate():
	#if not account.is_authenticated(scopes=['message_send']):
		account.authenticate()
		logging.critical("o365 emailer is not authenticated. Requires manual investigation.")

	example_mailbox = account.mailbox(resource=from_email)
	m = example_mailbox.new_message()
	m.to.add(to_email)
	m.subject = subject
	m.body = email_body
	m.send()

class html_table:

	def __init__(self, in_list):
		self.l = in_list
		self.start = '<table>'
		self.header = ''
		for th in in_list[0].keys():
			self.header += f'<th>{th}</th>'

		self.end = '</table>'
		self.row = ''
		self.guts()
		self.html = self.start + self.header + self.row + self.end

	def guts(self):
		#row = ''
		for i in self.l:
			row = '<tr>'
			for e in i.values():
				row += "<td>{}</td>".format(e)
			row += '</tr>'
			self.row += row