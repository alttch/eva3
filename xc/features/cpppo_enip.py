from eva.features import append_python_libraries, remove_python_libraries
from eva.features import download_phis, remove_phis
from eva.features import val_to_boolean

python_libraries = ['cpppo==4.0.6']

phis = [
    'https://get.eva-ics.com/phi/enip/enip_sensor.py',
    'https://get.eva-ics.com/phi/enip/enip_xvunit.py'
]


def setup(mods=False):
    mods = val_to_boolean(mods)
    append_python_libraries(python_libraries)

    if mods:
        download_phis(phis)


def remove(mods=False):
    remove_python_libraries(python_libraries)

    if mods:
        remove_phis(phis)
