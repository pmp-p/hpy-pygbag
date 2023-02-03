import textwrap
import re

from .autogenfile import AutoGenFile
from .parse import toC
from .ctx import autogen_ctx_h

CTX_NAME = '_HPyContext_s'

RST_DISCLAIMER = """
.. note: DO NOT EDIT THIS FILE!
    This file is automatically generated by {clsname}
    See also hpy.tools.autogen and hpy/tools/public_api.h

    Run this to regenerate:
        make autogen
"""

class AutoGenRstFile(AutoGenFile):
    LANGUAGE = 'rst'
    PATH = None
    DISCLAIMER = None

    def __init__(self, api):
        if self.DISCLAIMER is None and self.LANGUAGE == 'rst':
            self.DISCLAIMER = RST_DISCLAIMER
        self.api = api


class autogen_function_index(AutoGenRstFile):
    PATH = 'docs/api-reference/function-index.rst'
    LANGUAGE = 'rst'

    def generate(self):
        lines = []
        w = lines.append
        w('HPy Core API Function Index')
        w('###########################')
        w('')
        for func in self.api.functions:
            if func.name[0] != '_':
                w(f'* :c:func:`{func.name}`')
        return '\n'.join(lines)


GROUP_PATTERN = re.compile('Py(\\w+)_.*')

# Some C API functions are documented in very different pages.
SPECIAL_CASES = {
    'PyEval_SaveThread': 'init',
    'PyEval_RestoreThread': 'init',
    'PyEval_EvalCode': 'veryhigh',
}

# We assume that, e.g., prefix 'PyLong_Something' belongs to 'longobject.c' and
# its documentation is in '.../3/c-api/long.html'. In some cases, the prefix
# maps to a different page and this can be specified here. E.g.
# 'PyErr_Something' is documented in page '.../3/c-api/exceptions.html'
PREFIX_TABLE = {
    'err': 'exceptions'
}

class autogen_doc_api_mapping(AutoGenFile):
    PATH = 'hpy/tools/autogen/api_mapping.txt'
    LANGUAGE = 'txt'

    def _get_page(self, cpython_fun_name):
        if cpython_fun_name in SPECIAL_CASES:
            return SPECIAL_CASES[cpython_fun_name] + '.html'

        first_underscore = cpython_fun_name.find('_')
        if cpython_fun_name.startswith('Py') and first_underscore != -1:
            prefix = cpython_fun_name[2:first_underscore].lower()
            return PREFIX_TABLE.get(prefix, prefix) + '.html'
        else:
            return 'abstract.html'

    def generate(self):
        lines = []
        w = lines.append
        max_width0 = 0
        max_width1 = 0
        rows = []
        for func in self.api.functions:
            if not func.cpython_name:
                continue
            page = self._get_page(func.cpython_name)
            col0 = f'`{func.cpython_name} <https://docs.python.org/3/c-api/{page}#c.{func.cpython_name}>`_'
            col1 = f':c:func:`{func.name}`'
            rows.append((col0, col1))
            max_width0 = max(max_width0, len(col0))
            max_width1 = max(max_width1, len(col1))

        sep = '=' * max_width0 + ' ' + '=' * max_width1
        w(sep)
        w('C API function'.ljust(max_width0) + ' HPY API function')
        w(sep)
        for row in rows:
            w(f'{row[0].ljust(max_width0)} {row[1]}')
        w(sep)
        return textwrap.indent('\n'.join(lines), ' ' * 4)


class autogen_hpy_ctx(AutoGenRstFile):
    PATH = 'docs/api-reference/hpy-ctx.rst'

    def generate(self):
        lines = []
        w = lines.append
        w(textwrap.dedent(
            '''
            HPy Context
            ===========
            
            The ``HPyContext`` structure is also part of the API since it provides handles
            for built-in objects. For a high-level description of the context, please also
            read :ref:`api:hpycontext`.
            
            .. warning:: It is fine to use handles from the context (e.g. ``ctx->h_None``)
                but it is **STRONGLY** discouraged to directly call any context function.
                This is because, for example, when compiling for :term:`CPython ABI`, the
                context functions won't be used.
            '''))
        # Put all variable declarations into a list in order
        # to be able to sort them by their given context index.
        var_decls = list(self.api.variables)

        # sort the list of var declaration by 'decl.ctx_index'
        var_decls.sort(key=lambda x: x.ctx_index)

        w(f'.. c:struct:: {CTX_NAME}')
        w(f'    :module: {autogen_ctx_h.PATH}')
        w('')
        w(f'    .. c:member:: const char *{CTX_NAME}.name')
        w('')
        w(f'    .. c:member:: int {CTX_NAME}.abi_version')
        for var in var_decls:
            w('')
            w(f'    .. c:member:: {toC(var.node)}')
        return '\n'.join(lines)

