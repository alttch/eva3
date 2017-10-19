from eva.client.apiclient import APIClient

api = APIClient()
api.set_key('test1')
api.set_uri('http://localhost:828')
code, result = api.call('test')
print(result)
