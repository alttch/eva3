#!/usr/bin/env python3

import os
import sys
import json

dir_lib = os.path.dirname(os.path.realpath(__file__)) + '/../../lib'
sys.path.append(dir_lib)

from eva.client import apiclient

api = apiclient.APIClientLocal('uc')

api.ssl_verify(False)

# call EVA API function
print('Successful call:')
code, result = api.call('test')
print('CODE %u' % code)
print(json.dumps(result, indent = 4, sort_keys = True))

# call EVA API function with params
print('Non-existing item:')
code, result = api.call('state', { 'i': 'this_item_doesnt_exist' })
print('CODE %u' % code)
print(json.dumps(result, indent = 4, sort_keys = True))

# failed call
print('Failed call:')
code, result = api.call('cmd', {
    'c': 'test',
    'a': '1 2 3',
    'w': 10
    })
print('CODE %u' % code)
print(json.dumps(result, indent = 4, sort_keys = True))

# timeout
print('Timeout:')
api.set_timeout(2)
code, result = api.call('cmd', { 'c': 'test', 'w': 10 })
print('CODE %u' % code)
print(json.dumps(result, indent = 4, sort_keys = True))

# call unknown function
print('Unknown function:')
code, result = api.call('this_function_doesnt_exist')
print('CODE %u' % code)
print(json.dumps(result, indent = 4, sort_keys = True))

# call with invalid key
print('Invalid key:')
api.set_key('THIS_KEY_IS_INVALID')
code, result = api.call('test')
print('CODE %u' % code)
print(json.dumps(result, indent = 4, sort_keys = True))

# server error
print('Server error:')
api.set_uri('http://127.0.0.1:99999')
code, result = api.call('test')
print('CODE %u' % code)
print(json.dumps(result, indent = 4, sort_keys = True))

# call with API not initialized
print('API not initialized:')
api.set_uri(None)
api.set_product(None)
code, result = api.call('test')
print('CODE %u' % code)
print(json.dumps(result, indent = 4, sort_keys = True))
