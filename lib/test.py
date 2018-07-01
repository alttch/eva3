import importlib
import threading
import sys
import eva.core

d = 'test.basic'

phi_id, lpi_id = d.split('.')

phi_mod = importlib.import_module('eva.uc.drivers.phi.' + phi_id)
lpi_mod = importlib.import_module('eva.uc.drivers.lpi.' + lpi_id)

print('Driver: %s' % d)
print('PHI API: %u' % phi_mod.__api__)
print('PHI author: %s' % phi_mod.__author__)
print('PHI version: %s' % phi_mod.__version__)
print('PHI description: %s' % phi_mod.__description__)
print('PHI license: %s' % phi_mod.__license__)
print('LPI API: %u' % lpi_mod.__api__)
print('LPI author: %s' % lpi_mod.__author__)
print('LPI version: %s' % lpi_mod.__version__)
print('LPI description: %s' % lpi_mod.__description__)
print('LPI license: %s' % lpi_mod.__license__)

e = threading.Event()

driver = lpi_mod.LPI(phi=phi_mod.PHI)
status = driver.state(cfg = {'port': [ 'i3', 'i4', 'i1' ] })
print(status)
t = threading.Thread(target = driver.action, args=('111', 1, None, { 'port': [ 'i2', '4'] }, eva.core.timeout))
t.start()
t.join(1)
driver.terminate('111')
t.join(eva.core.timeout)
result = driver.get_result('111')
print(result)
print(driver.state(cfg={'port': 4}))
sys.exit()





status = driver.state(cfg = {'port': [ '2' ] })
print(status)
result = driver.action('222', status=0, cfg={ 'port': 11 })
print(result)
status = driver.state(cfg = {'port': [ '2' ] })
print(status)
status = driver.state(cfg = {'port': [ '4' ] })
print(status)
status = driver.state(cfg = {'port': [ '2', 'i4' ] })
print(status)
print(driver.get_result('111'))
print(driver.get_result('222'))
print(driver.get_result('333'))
