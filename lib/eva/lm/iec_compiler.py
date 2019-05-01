class CompilerError(Exception): pass

def gen_code_from_fbd(fbd, indent=4):

    def _fbparam_code(param):
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
        if a < len(input_args) - 1:
            args_code += ','
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
