#!/usr/bin/python2

import requests
from time import sleep
try:
	import simplejson as json
except ImportError:
	import json

class TokenExpired(Exception):
	pass

class ServerOverloaded(Exception):
	pass

# decorators
def needs_edit_token(func):
	def api_edit_runner(self, *args, **kwargs):
		for tries in range(0, 2):
			try:
				return func(self, *args, **kwargs)
			except TokenExpired:
				self._get_edit_token()
	return api_edit_runner


class WikiBaseLowAPI(object):
	def __init__(self, username, password, endpoint="https://www.wikidata.org/w/api.php", bot=False, maxlag=5):
		self.username = username
		self.endpoint = endpoint
		self.bot = bot
		self.maxlag = maxlag
		self.cookiejar = {}
		self._login(password)
		self.edit_token = None

	# entities
	def get_entities(self, ids, **optargs):
		qids = '|'.join(ids) if isinstance(ids, list) else ids
		r = self._get(action="wbgetentities", ids=qids, **optargs)
		return r

	# claims
	def get_claims(self, entity=None, claim=None, property=None, **optargs):
		r = self._get(action="wbgetclaims", entity=entity, claim=claim, property=property, **optargs)
		return r

	@needs_edit_token
	def add_claim(self, entity, property, value, summary, **optargs):
		r = self._post_t(action="wbcreateclaim", entity=entity, property=property, value=json.dumps(value),
		                 summary=summary, snaktype="value", **optargs)
		return r

	@needs_edit_token
	def del_claims(self, ids, summary, **optargs):
		qids = '|'.join(ids) if isinstance(ids, list) else ids
		r = self._post_t(action="wbremoveclaims", claim=ids, summary=summary, **optargs)
		return r

	@needs_edit_token
	def set_claim(self, claim, value, summary, **optargs):
		r = self._post_t(action="wbsetclaimvalue", claim=claim, value=json.dumps(value),
		                 summary=summary, snaktype="value", **optargs)
		return r

	# internal
	def _get_edit_token(self):
		r = self._get(action="tokens")
		assert r["tokens"]["edittoken"]
		self.edit_token = r["tokens"]["edittoken"]
		# a._get(action="query", prop="info", titles="Q42", intoken="edit")
		# ["query"]["pages"]["138"]["edittoken"]

	def _login(self, password):
		r = self._post(action="login", lgname=self.username, lspassword=password)
		if r["login"]["result"] == "NeedToken":
			r = self._post(action="login", lgname=self.username, lgpassword=password, lgtoken=r["login"]["token"])
		assert r["login"]["result"] == "Success"

	def _post_t(self, **params):
		params.update({
			"token": self.edit_token,
			"bot": 1 if self.bot else None,
		})
		data = self._post(**params)
		if "error" in data and data["error"]["code"] == "badtoken":
			raise TokenExpired("badtoken")
		return data

	def _get(self, **params):
		return self._http('GET', params)

	def _post(self, **params):
		return self._http('POST', params)

	def _http(self, method, params):
		params.update({
			"format": "json",
			"maxlag": self.maxlag,
		})
		for tries in range(0, 3):
			if method == 'GET':
				r = requests.get(self.endpoint, params=params, cookies=self.cookiejar)
			elif method == 'POST':
				r = requests.post(self.endpoint, params=params, cookies=self.cookiejar)
			data = r.json()
			if "error" in data and data["error"]["code"] == "maxlag":
				sleep(5)
			else:
				break
		if "error" in data and data["error"]["code"] == "maxlag":
			raise ServerOverloaded("Retry limit exceeded. Server reported: %s" % data["error"]["info"])
		self.cookiejar.update(r.cookies)
		return data
