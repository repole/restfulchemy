"""
Enables a registry of
:class:`Resource <restfulchemy.resource.ModelResource>` classes.

This allows for string lookup of resources, making it easier to
reference them dynamically and avoid circular dependencies.

.. warning::

    This module is treated as private API.
    Users should not need to use this module directly.

This module was taken directly from Marshmallow. The only difference
is that it serves as a registry of resources rather than schemas.
Please see below for the appropriate Marshmallow attribution.

Copyright 2015 Steven Loria

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""
from __future__ import unicode_literals

from marshmallow.exceptions import RegistryError

# {
#   <class_name>: <list of class objects>
#   <module_path_to_class>: <list of class objects>
# }
_registry = {}


def register(classname, cls):
    """Add a class to the registry of resource classes.

    When a class is registered, an entry for both its classname and
    its full, module-qualified path are added to the registry.

    Example: ::

        class MyClass:
            pass

        register('MyClass', MyClass)
        # Registry:
        # {
        #   'MyClass': [path.to.MyClass],
        #   'path.to.MyClass': [path.to.MyClass],
        # }

    :param str classname: Name of the class to be registered.
    :param cls: The class to be registered.

    """
    # Module where the class is located
    module = cls.__module__
    # Full module path to the class
    # e.g. user.schemas.UserSchema
    fullpath = '.'.join([module, classname])
    # If the class is already registered; need to check if the entries are
    # in the same module as cls to avoid having multiple instances of the same
    # class in the registry
    if classname in _registry and not \
            any(each.__module__ == module for each in _registry[classname]):
        _registry[classname].append(cls)
    else:
        _registry[classname] = [cls]

    # Also register the full path
    _registry.setdefault(fullpath, []).append(cls)
    return None


def get_class(classname, all=False):
    """Retrieve a class from the registry.

    :param str classname: Name of the class to be retrieved.
    :param bool all: If `True`, return all classes registered using
        the given class name.
    :raise: :exc:`~marshmallow.exceptions.RegistryError` if the class
        cannot be found or if there are multiple entries for the given
        class name and ``all`` is not `True`.
    :return: The class matching the name provided if previously
        registered, or potentially a list of classes if ``all`` is
        `True`.

    """
    try:
        classes = _registry[classname]
    except KeyError:
        raise RegistryError('Class with name {0!r} was not found. You may need '
                            'to import the class.'.format(classname))
    if len(classes) > 1:
        if all:
            return _registry[classname]
        raise RegistryError('Multiple classes with name {0!r} '
                            'were found. Please use the full, '
                            'module-qualified path.'.format(classname))
    else:
        return _registry[classname][0]
