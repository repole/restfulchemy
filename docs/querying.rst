.. _querying:
.. module:: restfulchemy

Querying
========

Say you’re building an API for your music collection, and you want to be
able to accept query params and use them to filter results. An example
using Flask might look like:

.. code:: python

    from flask import Flask
    from flask import request
    import inflection
    from models import *
    from restfulchemy.schema import ModelSchema
    from restfulchemy.resource import ModelResource
    from restfulchemy.router import generic_api_router
    from restfulchemy import class_registry

    # Should handle this in a separate file and import these...
    # Create schemas for your models
    # Fields are auto generated based on the SQLAlchemy model using
    # restfulchemy's built in ModelConverter. Any field can easily be
    # overriden to support hiding a field, marking it as read only,
    # or customized in pretty much any other way.
    # Overriding ModelSchema and using a custom ModelConvert is also
    # an option.
    class AlbumSchema(ModelSchema):
       class Meta:
           model = Album

    # Create a resource for your schema
    class AlbumResource(ModelResource):
        class Meta:
            schema_class = AlbumSchema

    # Also be sure to either create schemas and resources for all your
    # other models, or expliclity exclude relationship fields on your
    # schemas that may reference models that don't have associated
    # schemas and resources.
    # Or in simpler terms, if you want to be able to embed tracks in
    # an album resource, you need to have defined a tracks resource.


    @app.route("/api/<path:path>", methods=["GET"])
    def api_router(path):
        """Generic API router.

        You'll probably want to be more specific with your routing.

        """
        # get your SQLAlchemy db session however you normally would
        db_session = ...
        # query params are used to parse fields to include, embeds,
        # sorts, and filters.
        query_params = request.values.to_dict()
        # Using the path, figure out which ModelResource is being
        # requested. /tracks for example gets converted to
        # TrackResource with the help of the inflection library.
        split_path = path.split("/")
        resource_class_name = inflection.camelize(
            inflection.singularize(split_path[0]))+"Resource"
        # Every previously defined class can be easily accessed by name
        # via class_registry look up.
        resource_class = class_registry.get_class(resource_class_name)
        resource = resource_class(db_session=db_session)
        return simplejson.dumps(
            generic_api_query_router("GET", path, resource, query_params))

Note the use of the ``generic_api_router`` is very much optional and is used
purely for brevity here. Separate end points for each resource type could, and
probably should, be used in most situations.

Once a resource has an endpoint set up for it, some very powerful filtering
can be done.

Filtering by Unique Identifier
------------------------------
Access individual resources using their primary key value (or setting a custom
field to use as an ID on the ModelResource object):

``/api/albums/2``

.. code:: javascript

    {
        "album_id": 2,
        "artist": "/albums/2/artist",
        "self": "/albums/2",
        "title": "Balls to the Wall",
        "tracks": "/albums/2/tracks"
    }


Collection Filtering
--------------------
By default, any field or nested resource field that isn't `load_only` can be
queried. This can be turned on or off on a field by field basis if desired.

Query for things that are >, >=, =<, <, != by appending -gt, -gte,
-lt, -lte, -ne respectively to the parameter name.

``/api/albums?album_id-lte=10&album_id-gt>8``

.. code:: javascript

    [
        {
            "album_id": 9,
            "artist":  "/albums/9/artist",
            "self": "/albums/9",
            "title": "Plays Metallica By Four Cellos",
            "tracks": "/albums/9/tracks"
        },
        {
            "album_id": 10,
            "artist":  "/albums/10/artist",
            "self": "/albums/10",
            "title": "Audioslave",
            "tracks": "/albums/10/tracks"
        }
    ]


Query text fields for partial matches using -like.

``/api/albums?albums?title-like=salute``

.. code:: javascript

    [
        {
            "album_id": 1,
            "artist": {
                "self": "/artists/1"
            },
            "self": "/albums/1",
            "title": "For Those About To Rock We Salute You",
            "tracks": "/albums/1/tracks"
        }
    ]


Advanced Filtering
------------------
Query using complex MQLAlchemy style filters:

``/api/tracks?query={"$and":[{"unit_price":{"$lte":1}},{"album.album_id":2}]}``

.. code:: javascript

    [
        {
            "album": {
                "self": "/albums/2"
            },
            "bytes": 5510424,
            "composer": null,
            "genre": {
                "self": "/genres/1"
            },
            "media_type": {
                "self": "/mediaTypes/2"
            },
            "milliseconds": 342562,
            "name": "Balls to the Wall",
            "playlists": "/tracks/2/playlists",
            "self": "/tracks/2",
            "track_id": 2,
            "unit_price": 0.99
        }
    ]


Embedding Relationships and Fields
----------------------------------
Embed full relationships or fields of relationships:

``/api/albums/2?embeds=artist,tracks.name&limit=1``

.. code:: javascript

    {
        "album_id": 2,
        "artist": {
            "artistId": 2,
            "name": "Accept",
            "self": "/artists/2"
        },
        "self": "/albums/2",
        "title": "Balls to the Wall",
        "tracks": [
            {
                "name": "Balls to the Wall"
            }
        ]
    }


Choose fields you want returned explicitly:

``/api/albums/2?fields=title,album_id``

.. code:: javascript

    {
        "album_id": 2,
        "title": "Balls to the Wall"
    }


Offset, Limit, and Pagination
-----------------------------
Use limit for any end point:

``/api/albums&limit=2``

.. code:: javascript

    [
        {
            "album_id": 1,
            "artist": "/albums/1/artist",
            "self": "/albums/1",
            "title": "For Those About To Rock We Salute You",
            "tracks": "/albums/1/tracks"
        },
        {
            "album_id": 2,
            "artist": "/albums/2/artist",
            "self": "/albums/2",
            "title": "Balls to the Wall",
            "tracks": "/albums/2/tracks"
        }
    ]


Use offset for any end point:

``/api/albums&limit=1&offset=1``

.. code:: javascript

    [
        {
            "album_id": 2,
            "artist": "/albums/2/artist",
            "self": "/albums/2",
            "title": "Balls to the Wall",
            "tracks": "/albums/2/tracks"
        }
    ]


Paginate any end point (limit can be used to set page size):

``/api/albums&page=2limit=5``

.. code:: javascript

    [
         {
            "album_id": 6,
            "artist": "/albums/6/artist",
            "self": "/albums/6",
            "title": "Jagged Little Pill",
            "tracks": "/albums/6/tracks"
        },
        {
            "album_id": 7,
            "artist":  "/albums/7/artist",
            "self": "/albums/7",
            "title": "Facelift",
            "tracks": "/albums/7/tracks"
        },
        {
            "album_id": 8,
            "artist":  "/albums/8/artist",
            "self": "/albums/8",
            "title": "Warner 25 Anos",
            "tracks": "/albums/8/tracks"
        },
        {
            "album_id": 9,
            "artist":  "/albums/9/artist",
            "self": "/albums/9",
            "title": "Plays Metallica By Four Cellos",
            "tracks": "/albums/9/tracks"
        },
        {
            "album_id": 10,
            "artist":  "/albums/10/artist",
            "self": "/albums/10",
            "title": "Audioslave",
            "tracks": "/albums/10/tracks"
        }
    ]


Convert Fields to camelCase
---------------------------

Schemas can easily be defined to serialize and deserialize using camelCase
field names to be more JavaScript friendly.

.. code:: python

    class AlbumSchema(ModelResourceSchema):
        class Meta:
            model = Album
            converter = CamelModelResourceConverter

``/api/albums/2``

.. code:: javascript

    {
        "albumId": 2,
        "artist": "/albums/2/artist",
        "self": "/albums/2",
        "title": "Balls to the Wall",
        "tracks": "/albums/2/tracks"
    }