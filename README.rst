RESTfulchemy
============

|Build Status| |Coverage Status| |Docs|

Get, update, and create SQLAlchemy objects using query string parameters.

Shares some similarities with projects like Django-Tastypie and Flask-RESTful,
but depends on the SQLAlchemy ORM and otherwise leaves more decisions up to
the user.

Why? Aren't there a million other libraries with similar goals?
---------------------------------------------------------------

There are, but they didn't offer quite the flexibility I'm looking for.

The first thing I wanted was more power over was querying my SQLAlchemy
models via query string parameters. I wanted to be able to do more than
simply check equality on top level attributes. I wanted to be able to
query sub resources, check for attributes greater than or less than a
supplied input, and do all of that with explicitly defined permissions.

For more info on this portion of the library, see the "Querying" section.

The second thing I wanted was to be able to create and update SQLAlchemy
objects and their and sub resources using POST/PUT form input.
Imagine a scenario where you want a user to be able to create an album and
all associated tracks with it using a single POST request. In a traditional
RESTful API, you'd make a POST request to create the album, then numerous
additional POST requests to create each track. This can certainly get the
job done, but often times in similar situations, we want a sort of all in
one transaction, where if any part of the process fails, all of it should
fail. Traditional RESTful APIs make this inherently difficult to accomplish.

One of the goals of RESTfulchemy is to provide a generalized way of creating
and updating objects along with their sub resources all in one request. This
is done by providing a clearly defined syntax for accessing sub resources of
the object you're attempting to update.

See below in the "Updating Objects" section for an example of how this works.



Current Status
--------------

This is basically in alpha status. Things are still undergoing
constant change, and interfaces may change, but there are no known
bugs at this point.


Querying
--------

Say you’re building an API for your music collection, and you want to be
able to accept query params and use them to filter results for all
fields except "unit_price". An example using Flask might look like:

.. code:: python

    @app.route("/api/tracks", methods=["GET"])
    def get_tracks():
        # get your SQLAlchemy db session however you normally would
        db_session = ...
        tracks = get_resources(
            db_session,
            Track,    # SQLAlchemy Track model
            request.values.to_dict(),
            whitelist=[
                "name",
                "track_id",
                "album_id",
                "media_type_id",
                "genre_id",
                "composer",
                "milliseconds",
                "bytes",
                "artist.name",
                "album.name"
            ]
        matching_tracks = query.all()
        # return however you choose
        return ...

The result of this is being able to write queries like:

/api/tracks?genre=Rock&milliseconds-lte=5000000&artist.name=Aerosmith&order_by=name~ASC

A few nice things this allows you to do:

- Query for things that are >, >=, =<, <, != by appending -gt, -gte,
  -lt, -lte, -ne respectively to the parameter name.
- Query text fields for partial matches using _~like.
- Query a relationship, such as artist and album.
- Sort by any attribute of Track. To apply a secondary sort, simply
  separate with a dash (-).
- You can also pass pagination parameters, or use limit and offset in
  the url.

**More Complex Example**

You can append a special parameter ~query, and set it equal to a url
encoded MongoDB style JSON query to perform even more complex queries.

    /api/tracks?query={“$or”: [{“genre”: “Rock”}, {“artist.name”:“Aerosmith”}]}

Note that the value there is not url encoded for the sake of making the
example easier to understand. See MQLAlchemy for more details on what
portions of MongoDB query syntax are available for this.

Updating Objects
----------------

Again, using Flask and the same API example as above:

.. code:: python

    @app.route("/api/tracks/<track_id>", methods=["PUT"])
    def update_track(track_id):
        # get your database session however you normally would
        db_session = ...
        # get the instance of the track we want to update
        track = db_session.query(Track).filter(
            Track.track_id == track_id).first()
        update_resource(
            db_session,
            track,
            put_param_dict,
            whitelist=[
                "name",
                "track_id",
                "album_id",
                "media_type_id",
                "genre_id",
                "composer",
                "milliseconds",
                "bytes",
                "artist._add_",
                "artist._remove_",
                "artist.name",
                "album._create_",
                "album._add_",
                "album._remove_",
                "album.name"
            ]
        )
        db_session.commit()
        # return however you choose
        return ...

Now say we submit a PUT request to /api/tracks/1 with the parameters:

-  media_type_id=2
-  artist.id-artist_id-1._set_=True

   -  Set track.artist to an already existing artist (the db will be
      queried for an artist that has an artist_id of 1). Whitelisting
      “artist._add_” allows this.
   -  In the process of setting the artist to a different one, the old
      one must of course must be removed since this relationship
      reference does not use a list. This is why “artist._remove_” must
      be included in the whitelist. Note that this won’t actually cause
      the artist to be deleted from the database (unless you have some
      cascade delete set up).
   -  You may instead use "artist._set_" in the whitelist to implicitly
      allow _add_ and _remove_ for a non list using relationship.
   -  The _set_ at the end of "artist.id-artist_id-1._set_=True" works
      different than _add_ would. _set_ states to try to overwrite any
      previous artist value if one existed and if permission is granted
      via the whitelist. If _add_ was used instead, the command would
      only work if artist previously had no value. For a list relation
      rather than a non list relation, only _add_ is valid.

-  The $id attribute is used to access a sub-object of a relationship
   field (whether it’s a list based relationship or not does not
   matter).

   -  There are two formats for an $id key:
      - Standard: $id:primary_key_col_1=val1:primary_key_col_2=val2
      - URL Safe: id-primary_key_col_1-val1-primary_key_col_2-val2

-  album._new_._add_=True

   -  Set track.album to a newly created album.

-  album._new_.name=My New Album

   -  Give that newly created album a name.

Creating Objects
----------------

Nearly identical to updating, with a few small differences.

.. code:: python

    @app.route("/api/tracks/", methods=["POST"])
    def create_track():
        # get your database session however you normally would
        db_session = ...
        track = create_resource(
            db_session,
            Track,    # note that this is the actual model class
            query_string,
            whitelist=[
                "name",
                "track_id",
                "album_id",
                "media_type_id",
                "genre_id",
                "composer",
                "milliseconds",
                "bytes",
                "artist._set_",
                "artist.name",
                "album._create_",
                "album._remove_",
                "album._add_",
                "album.name"
            ]
        )
        db_session.commit()
        # return however you choose
        return ...

$ vs underscore
---------------

In a number of places, a $ character can be used rather than leading
and trailing underscores. For instance, using $add rather than _add_ is
perfectly acceptable. The latter is generally preferred as it is URL
safe, and in all likelihood you're using this library as part of a web
service.

Special query parameter names
-----------------------------

In the above examples, some query parameter names are used that may
conflict with your SQLAlchemy object attribute names. If you have an
object with any of "query", "order_by", "offset", or "limit", you can
instead explicitly use non default options for these query parameters.
See `get_resources` for more info.

Contributing
------------

Submit a pull request and make sure to include an updated AUTHORS
with your name along with an updated CHANGES.rst.

License
-------

MIT

.. |Build Status| image:: https://travis-ci.org/repole/restfulchemy.svg?branch=master
   :target: https://travis-ci.org/repole/restfulchemy
.. |Coverage Status| image:: https://coveralls.io/repos/repole/restfulchemy/badge.svg?branch=master
   :target: https://coveralls.io/r/repole/restfulchemy?branch=master
.. |Docs| image:: https://readthedocs.org/projects/restfulchemy/badge/?version=latest
   :target: http://restfulchemy.readthedocs.org/en/latest/
