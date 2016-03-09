=======
Changes
=======

Release 0.3.0  (in progress)
============================

Features added
--------------
* Serialization and deserialization provided largely in part thanks to
  Marshmallow-SQLAlchemy with some customizations built on top.
* ``ModelResource`` class created.
* Field name conversion on serialization and deserialization available
  thanks to Marshmallow dump_to and load_from field attributes. Automatically
  handled by ``ModelResource``. Makes it possible for an API to expose
  camelCase field names despite the schema field names using underscores.
* Query whitelisting or blacklisting based on field load_only property.
  Automatically handled by ``ModelResource``.
* ``EmbeddedField`` added to allow sub resource embedding and nested
  serialization and deserialization.

Incompatible changes
--------------------
* This is essentially a complete overhaul. If the prior library was more
  mature or widely used, I'd release this as a separate library.
* The below functions that have been removed have mostly been reincorporated
  as part of the ModelResource class, and now depend on taking in a dict of
  JSON data rather than form parameters.
* Functions renamed: ``apply_order_by`` renamed to ``apply_sorts``.
* Functions moved: ``parse_filters`` to ``restfulchemy.parser``, and both
  ``apply_offset_and_limit`` ``apply_sorts`` to ``restfulchemy.query_builder``.
* Functions removed: ``get_class_attributes``,  ``get_class_attributes``,
  ``get_alchemy_primary_keys``, ``get_primary_key_dict``, ``create_resource``,
  ``get_resources_query``, ``get_resources``, ``get_resource``, and
  ``update_resource``.
* Functions with modified signatures: ``parse_filters``, ``apply_sorts``,
  ``apply_offset_and_limit``.


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