RESTfulchemy
============

|Build Status| |Coverage Status| |Docs| |License| |Python Versions|
|Python Implementations| |Format|

Get, update, and create SQLAlchemy objects using query string parameters.

Shares some similarities with projects like Django-Tastypie and Flask-RESTful,
but depends on the SQLAlchemy ORM and otherwise leaves more decisions up to
the user.

Getting
-------

Say you’re building an API for your music collection, and you want to be
able to accept query params and use them to filter results for all
fields except "unit_price". An example using Flask might look like:

.. code:: python

    @app.route("/api/tracks", methods=["GET"])
    def get_tracks():
        # get your database session however you normally would
        db_session = ...
        tracks = get_resources(
            db_session,
            Track,
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

/api/tracks?genre=Rock&milliseconds_~lte=5000000&artist.name=Aerosmith&~order_by=name~ASC

A few nice things this allows you to do:

- Query for things that are >, >=, =<, <, != by appending _~gt, _~gte,
  _~lt, _~lte, _~ne respectively to the parameter name.
- Query text fields for partial matches using _~like.
- Query a relationship, such as artist and album.
- Sort by any attribute of Track. To apply a secondary sort, simply
  separate with a dash (-).
- You can also pass pagination parameters, or use ~limit and ~offset in
  the url.

**More Complex Example**

You can append a special parameter ~query, and set it equal to a url
encoded MongoDB style JSON query to perform even more complex queries.

    /api/tracks?~query={“$or”: [{“genre”: “Rock”}, {“artist.name”:“Aerosmith”}]}

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
                "artist.~add",
                "artist.~remove",
                "artist.name",
                "album.~create",
                "album.~add",
                "album.~remove",
                "album.name"
            ]
        )
        db_session.commit()
        # return however you choose
        return ...

Now say we submit a PUT request to /api/tracks/1 with the query parameters:

-  media_type_id=2
-  artist.~id:artist_id=1.~set=True

   -  Set track.artist to an already existing artist (the db will be
      queried for an artist that has an artist_id of 1). Whitelisting
      “artist.~add” allows this.
   -  In the process of setting the artist to a different one, the old
      one must of course must be removed since this relationship
      reference does not use a list. This is why “artist.~remove” must
      be included in the whitelist. Note that this won’t actually cause
      the artist to be deleted from the database (unless you have some
      cascade delete set up).
   -  You may instead use "artist.~set" in the whitelist to implicitly
      allow ~add and ~remove for a non list using relationship.
   -  The ~set at the end of "artist.~id:artist_id=1.~set=True" works
      different than ~add would. ~set states to try to overwrite any
      previous artist value if one existed and if permission is granted
      via the whitelist. If ~add was used instead, the command would
      only work if artist previously had no value. For a list relation
      rather than a non list relation, only ~add is valid.

-  The ~id attribute is used to access a sub-object of a relationship
   field (whether it’s a list based relationship or not does not
   matter).

   -  The format of the ~id attribute is
      ~id:primary_key_col_1=val:primary_key_col_2=val

-  album.~new.~add=True

   -  Set track.album to a newly created album.

-  album.~new.name=My New Album

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
                "artist.~set",
                "artist.name",
                "album.~create",
                "album.~remove",
                "album.~add",
                "album.name"
            ]
        )
        db_session.commit()
        # return however you choose
        return ...

$ vs ~
------

Both $ and ~ work identically and can be used interchangeably.
~ was included mainly because it is url friendly.

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
.. |Version| image:: https://pypip.in/version/restfulchemy/badge.svg
   :target: https://pypi.python.org/pypi/restfulchemy/
   :alt: Latest Version
.. |Python Versions| image:: https://pypip.in/py_versions/restfulchemy/badge.svg
   :target: https://pypi.python.org/pypi/restfulchemy/
   :alt: Supported Python versions
.. |Python Implementations| image:: https://pypip.in/implementation/restfulchemy/badge.svg
   :target: https://pypi.python.org/pypi/restfulchemy/
   :alt: Supported Python implementations
.. |License| image:: https://pypip.in/license/restfulchemy/badge.svg
   :target: https://pypi.python.org/pypi/restfulchemy/
   :alt: License
.. |Format| image:: https://pypip.in/format/restfulchemy/badge.svg
   :target: https://pypi.python.org/pypi/restfulchemy/
   :alt: Download format