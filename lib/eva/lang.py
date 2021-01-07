import gettext
from pathlib import Path

default_localedir = Path(__file__).absolute().parents[1] / 'locales'


def _find_el(localedir, lang, document_name=None):
    el = None
    bases = ['messages']
    if document_name:
        parts = document_name.split('/')
        for n in range(len(parts)):
            bases.append('/'.join(parts[:n + 1]))
    for base in reversed(bases):
        try:
            el = gettext.translation(base,
                                     localedir=localedir,
                                     languages=[lang])
            import eva.core
            if eva.core.config.development:
                clear_cache()
            break
        except FileNotFoundError:
            pass
    return el


def _convert_str(text, el=None):
    if el is None:
        return text
    lines = text.replace('\r', '').split('\n')

    for i, l in enumerate(lines):
        line = l.strip()
        if line:
            ls = l.lstrip()
            rs = l.rstrip()
            left_side = l[:len(l) - len(ls)] if len(ls) != len(l) else ''
            right_side = l[-(len(l) - len(rs)):] if len(rs) != len(l) else ''
            x = left_side + el.gettext(line) + right_side
            lines[i] = x

    return '\n'.join(lines)


def convert_text(text, lang, document_name=None, localedir=default_localedir):
    return _convert_str(text, el=_find_el(localedir, lang, document_name))


def convert(obj,
            lang,
            document_name=None,
            localedir=default_localedir,
            _el=None):
    if _el is None:
        _el = _find_el(localedir, lang, document_name)
    if _el is None:
        return obj
    elif isinstance(obj, list):
        result = obj.copy()
        for i, v in enumerate(result):
            result[i] = convert(v, lang, _el=_el)
        return result
    elif isinstance(obj, dict):
        result = obj.copy()
        for i, v in result.items():
            result[i] = convert(v, lang, _el=_el)
        return result
    elif isinstance(obj, str):
        return _convert_str(obj, el=_el)
    else:
        return obj


def clear_cache():
    gettext._translations.clear()
