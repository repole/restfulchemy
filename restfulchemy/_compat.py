## -*- coding: utf-8 -*-\
"""
    restfulchemy._compat
    ~~~~~~~~~~~~~~~~~~~~

    Python2/Python3 support helper library.

    :copyright: (c) 2016 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""

import sys

if sys.version_info[0] == 2:    # pragma: no cover
    bytes = str
    str = unicode
else:    # pragma: no cover
    str = str
    bytes = bytes
