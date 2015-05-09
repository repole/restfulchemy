=======
Changes
=======

Release 0.2.1
===========================

Features added
--------------
* Added only_parse_complex as an optional parameter for parse_filters. 
  Useful in bulk update situations where standard query params are used
  for update statements rather than filters.


Release 0.2.0
===========================

Incompatible changes
--------------------
* $create no longer implicitly allows $add.
* $delete has been changed to $remove.
* $set added to allow both $add and $remove for a single relationship.

Documentation
-------------
* README.rst and docstrings updated with new $remove, $set, and $create rules.


Release 0.1.2
=============

Incompatible changes
--------------------
* get_resource() no longer erroneously accepts pagination params.

Documentation
-------------
* Updated a few function doc strings.


Release 0.1.1
=============

Incompatible changes
--------------------
* Changed license to MIT from BSD.
* Renamed test class from AlchemyUtilsTests to RESTfulchemyTests.
* Changed get_object to get_resource.
* Changed get_objects to get_resources.
* Changed update_object to update_resource.
* Changed create_object to create_resource.

Documentation
-------------
* Updated README.rst with badges for PyPI and readthedocs.
* Included install instructions for installing from source.