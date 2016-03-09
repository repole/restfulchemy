.. _why:

Why?
====

Aren't there a million other libraries with similar goals?
----------------------------------------------------------

There are, but they don't offer quite the same level of depth.

The first thing I wanted was more power over was querying my SQLAlchemy
models via query string parameters. I wanted to be able to do more than
simply check equality on top level attributes. I wanted to be able to
query sub resources, check for attributes greater than or less than a
supplied input, and do all of that with explicitly defined permissions.

For more info on this portion of the library, see the
:ref:`querying <querying>` section.

The second thing I wanted was to be able to create and update SQLAlchemy
objects and their and sub resources using POST/PUT/PATCH input.
Imagine a scenario where you want a user to be able to create an album and
all associated tracks with it using a single POST request. In a traditional
RESTful API, you might make a POST request to create the album, then numerous
additional POST requests to create each track. This can certainly get the
job done, but often times in similar situations, a sort of all in one
transaction is desired, where if any part of the process fails, all of it
should fail. Many RESTful API frameworks make this inherently difficult to
accomplish.

See the :ref:`creating and updating resources <creating_updating>` section for
an example of how this works.