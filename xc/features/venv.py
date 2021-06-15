from eva.features import OS_ID, OS_LIKE, UnsupportedOS
from eva.features import exec_shell, rebuild_python_venv, dir_eva
from eva.features import install_system_packages
from eva.features import val_to_boolean


def setup(from_scratch=False):
    from_scratch = val_to_boolean(from_scratch)
    if from_scratch:
        from eva.features import print_warn
        print_warn('Removing Python virtual environment')
        print('Removing venv...')
        # check to avoid rm at root
        if dir_eva:
            exec_shell(f'rm -rf {dir_eva}/python3')
        else:
            raise RuntimeError('EVA directory not detected')
    rebuild_python_venv()
