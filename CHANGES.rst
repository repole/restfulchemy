=======
Changes
=======

Release 0.3.0  (in progress)
============================

Features added
--------------
* Improved error reporting on exceptions. Any AlchemyUpdateException
  raised now includes a dict of fieldnames with lists of errors for
  that field.
* Ability to validate an update prior to executing it.
* Can now whitelist setting specifically only newly created object
  attributes within a relationship without having to simultaneously
  whitelist setting prior existing object's attributes. In other
  words, whitelisting 'tracks.$new.track_id' would allow the track_id
  of a newly created track for an album to be set, without giving
  permission at the same time to change track_id for any already
  existing track on that album.

Incompatible changes
--------------------
* $id field syntax overhauled to use only url safe characters.


Release 0.2.1
=============

Features added
--------------
* Added only_parse_complex as an optional parameter for parse_filters. 
  Useful in bulk update situations where standard query params are used
  for update statements rather than filters.


Release 0.2.0
=============

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