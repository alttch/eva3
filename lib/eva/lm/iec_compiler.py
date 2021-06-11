__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"


class CompilerError(Exception):
    pass


def gen_code_from_fbd(fbd, indent=4):

    def _fbparam_code(param):
        pt = param.get('type')
        if pt == 'var_in':
            return param['value']
        elif pt == 'const':
            result = param['value']
            try:
                result = float(param['value'])
                if result == int(result):
                    result = int(result)
            except:
                result = '\'' + result + '\''
            return result
        elif pt == 'block_out':
            v = param['value']
            if isinstance(v, list):
                block_id, block_out_var = v
            else:
                block_id, block_out_var = v, None
            result = '_BLOCK{}_OUT'.format(block_id)
            if block_out_var is not None:
                result += '[\'{}\']'.format(block_out_var)
            return result
        else:
            raise CompilerError('Invalid param type: {}'.format(pt))

    def _fbfunction_code(f, params):
        code = f + '('
        if params:
            for p, v in params.items():
                if isinstance(v, list):
                    code += '{}=['.format(p)
                    for vv in v:
                        code += '{},'.format(_fbparam_code(vv))
                    code += '],'
                else:
                    code += '{}={},'.format(p, _fbparam_code(v))
        code += ')'
        return code

    v = []
    func = fbd['function']
    result_vars = []
    fbd_body = sorted(fbd['body'].copy(), key=lambda k: k['id'])
    blocks = {}
    main_code = ''
    for block in fbd_body:
        blocks[block['id']] = block
        main_code += ' ' * indent + '_BLOCK{}_OUT={}\n'.format(
            block['id'],
            _fbfunction_code(block['function'], block.get('params', {})))
    args_code = ''
    input_args = fbd['input']
    for a in range(len(input_args)):
        args_code += input_args[a]['var']
        if 'default' in input_args[a]:
            args_code += '={}'.format(input_args[a]['var'],
                                      input_args[a]['default'])
        else:
            args_code += '=None'
        if a < len(input_args) - 1:
            args_code += ', '
    code = 'def {}({}):\n'.format(func, args_code)
    code += '{}'.format(main_code)
    output_args = fbd.get('output', [])
    for o in output_args:
        v = o['value']
        if isinstance(v, list):
            block_id, block_out_var = v
        else:
            block_id, block_out_var = v, None
        code += ' ' * indent + '{}=_BLOCK{}_OUT'.format(o['var'], block_id)
        if block_out_var is not None:
            code += '[\'{}\']'.format(block_out_var)
        result_vars.append(o['var'])
        code += '\n'
    code += ' ' * indent
    if not result_vars:
        code += 'return'
    elif len(result_vars) < 2:
        code += 'return {}'.format(result_vars[0])
    else:
        code += 'return {'
        for r in result_vars:
            code += '\'{}\':{},'.format(r, r)
        code += '}'
    return code


def gen_code_from_sfc(sfc):

    sfc_name = sfc['name']

    def _sparam_code(param):
        pt = param.get('type')
        if pt == 'const':
            result = param['value']
            try:
                result = float(param['value'])
                if result == int(result):
                    result = int(result)
            except:
                result = '\'' + result + '\''
            return result
        elif pt == 'var':
            return 'shared(\'__{}_{}\')'.format(sfc_name, param['value'])
        elif pt == 'var_shared':
            return 'shared(\'{}\')'.format(param['value'])
        elif pt == 'func':
            code = _sfunction_code(param['value']['func'],
                                   param['value']['params'])
            if 'func_var_out' in param['value']:
                code += '[\'{}\']'.format(param['value']['func_var_out'])
            return code
        else:
            raise CompilerError('Invalid param type: {}'.format(pt))

    def _sfunction_code(f, params):
        code = f + '('
        if params:
            for p, v in params.items():
                if isinstance(v, list):
                    code += '{}=['.format(p)
                    for vv in v:
                        code += '{},'.format(_sparam_code(vv))
                    code += '],'
                else:
                    code += '{}={},'.format(p, _sparam_code(v))
        code += ')'
        return code

    def _sfc_block_code(blocks, indent, thread_id):
        if not blocks:
            return None
        first_block_id = 0
        code = ' ' * indent + 'while True:\n'
        for b in blocks:
            code += ' ' * (indent + 4)
            if first_block_id:
                code += 'el'
            code += 'if __SFC_STEP == {}:\n'.format(b['id'])
            fncode = ''
            if 'func' in b:
                fncode = _sfunction_code(b['func'], b['params'])
            elif b['type'] == 'thread_start':
                for t_id in b['thread']:
                    fncode = ('__thread_{} = threading.Thread(' +
                              'target=__sfc_thread_{})\n').format(t_id, t_id)
                    fncode += ' ' * (indent +
                                     8) + '__thread_{}.start()'.format(t_id)
            elif b['type'] == 'thread_wait':
                for t_id in b['thread']:
                    fncode = '__thread_{}.join()'.format(t_id)
            if b['type'] == 'set':
                if b['var'] == 'out':
                    if thread_id != 0:
                        raise CompilerError(
                            'Variable "out" can be set only from main thread')
                    var_name = 'out'
                else:
                    var_name = b['var'] if b.get(
                        'var_shared') else '__{}_{}'.format(sfc_name, b['var'])
                if b.get('func_var_out'):
                    fncode += '[\'{}\']'.format(b['func_var_out'])
                code += ' ' * (indent + 8)
                if var_name != 'out':
                    code += 'set_shared(\'{}\', {})\n'.format(var_name, fncode)
                else:
                    if fncode:
                        code += 'out = {}\n'.format(fncode)
                    else:
                        var_name = b['var_in'] if b.get(
                            'var_in_shared') else '__{}_{}'.format(
                                sfc_name, b['var_in'])
                        code += 'out = shared(\'{}\')\n'.format(var_name)
            elif b['type'] == 'cond':
                code += ' ' * (indent + 8) + 'if {}:\n'.format(fncode)
                code += ' ' * (indent + 12) + '__SFC_STEP = {}\n'.format(
                    b['next'])
                code += ' ' * (indent + 8) + 'else:\n'
                code += ' ' * (indent + 12) + '__SFC_STEP = {}\n'.format(
                    b['next-false'])
            else:
                code += ' ' * (indent + 8) + fncode + '\n'
            if b['type'] != 'cond':
                if 'next' in b:
                    code += ' ' * (indent + 8) + '__SFC_STEP = {}\n'.format(
                        b['next'])
                else:
                    code += ' ' * (indent + 8) + 'break\n'
            if not first_block_id or b['id'] < first_block_id:
                first_block_id = b['id']
        if first_block_id:
            code = ' ' * indent + '__SFC_STEP = {}\n{}'.format(
                first_block_id, code)
            return code
        else:
            return None

    code_threads = {}
    for c in sfc['code-blocks']:
        thread_id = c['thread']
        # if thread_id > 0:
        indent = 4
        # else:
        # indent = 8
        code = _sfc_block_code(c.get('blocks', []), indent, thread_id)
        if code:
            code_threads[thread_id] = code
    sfc_code = ''
    for c, code in code_threads.items():
        if c > 0:
            sfc_code += 'def __sfc_thread_{}(*args, **kwargs):\n'.format(c)
            sfc_code += code
    sfc_code += '\ntry:\n' + code_threads[0]
    sfc_code += 'finally:\n'
    final_code = _sfc_block_code(sfc.get('final-blocks'), 4, 0)
    if final_code:
        sfc_code += final_code
    else:
        sfc_code += '    pass'
    if len(code_threads) > 1:
        sfc_code = 'import threading\n' + sfc_code
    return sfc_code
