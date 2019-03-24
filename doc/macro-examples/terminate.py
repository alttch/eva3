try:
    terminate(unit_id='tests/unit1')
except ResourceNotFound:
    print('no action running')
