import textwrap
import re

from .autogenfile import AutoGenFile
from .parse import toC
from .ctx import autogen_ctx_h
from .conf import (DOC_C_API_PAGES_SPECIAL_CASES,
                   DOC_MANUAL_API_MAPPING,
                   DOC_PREFIX_TABLE)


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
        functions = list(self.api.functions)
        # sort the list of functions by 'func.name'
        functions.sort(key=lambda x: x.name)
        for func in functions:
            if func.name[0] != '_':
                w(f'* :c:func:`{func.name}`')
        return '\n'.join(lines)


class AutoGenFilePart:
    PATH = None
    BEGIN_MARKER = None
    END_MARKER = None

    def __init__(self, api):
        self.api = api

    def generate(self, old):
        raise NotImplementedError

    def write(self, root):
        if not self.BEGIN_MARKER or not self.END_MARKER:
            raise RuntimeError("missing BEGIN_MARKER or END_MARKER")
        n_begin = len(self.BEGIN_MARKER)
        with root.join(self.PATH).open('r') as f:
            content = f.read()
        start = content.find(self.BEGIN_MARKER)
        if start < 0:
            raise RuntimeError(f'begin marker "{self.BEGIN_MARKER}" not found'
                               f'in file {self.PATH}')
        end = content.find(self.END_MARKER, start + n_begin)
        if end < 0:
            raise RuntimeError(f'end marker "{self.END_MARKER}" not found in'
                               f'file {self.PATH}')
        new_content = self.generate(content[(start+n_begin):end])
        with root.join(self.PATH).open('w') as f:
            f.write(content[:start + n_begin] + new_content + content[end:])


GROUP_PATTERN = re.compile('Py(\\w+)_.*')

class autogen_doc_api_mapping(AutoGenFilePart):
    PATH = 'docs/porting-guide.rst'
    BEGIN_MARKER = '.. mark: BEGIN API MAPPING\n'
    END_MARKER = '.. mark: END API MAPPING\n'

    def _get_page(self, cpython_fun_name):
        if cpython_fun_name in DOC_C_API_PAGES_SPECIAL_CASES:
            return DOC_C_API_PAGES_SPECIAL_CASES[cpython_fun_name] + '.html'

        first_underscore = cpython_fun_name.find('_')
        if cpython_fun_name.startswith('Py') and first_underscore != -1:
            prefix = cpython_fun_name[2:first_underscore].lower()
            return DOC_PREFIX_TABLE.get(prefix, prefix) + '.html'
        else:
            return 'abstract.html'

    def generate(self, old_content):
        table_directive = '.. _table-mapping:\n.. table:: Safe API function mapping\n'
        assert old_content.strip().startswith(table_directive)

        lines = []
        w = lines.append
        w(':widths: auto')
        w('')
        mapping = {x.cpython_name: x.name for x in self.api.functions if x.cpython_name}
        mapping.update(DOC_MANUAL_API_MAPPING)
        max_width0 = 0
        max_width1 = 0
        rows = []
        cpy_functions = list(mapping.keys())
        # sort the list of functions by 'cpython_name'
        cpy_functions.sort()
        for cpy_func in cpy_functions:
            assert cpy_func
            page = self._get_page(cpy_func)
            col0 = f'`{cpy_func} <https://docs.python.org/3/c-api/{page}#c.{cpy_func}>`_'
            col1 = f':c:func:`{mapping[cpy_func]}`'
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
        w('')
        return table_directive + textwrap.indent('\n'.join(lines), ' ' * 4)


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

