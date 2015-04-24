## -*- coding: utf-8 -*-\
"""
    restfulchemy.tests.__init__
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests for RESTfulchemy create, get, and update methods.

    :copyright: (c) 2015 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
import unittest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mqlalchemy.tests import models
from mqlalchemy import InvalidMQLException
import restfulchemy
from restfulchemy import update_resource, create_resource, \
    get_resource, get_resources, AlchemyUpdateException
import json


class AlbumPlus(models.Album):

    """Extension class of Album for test purposes."""

    test = object()


class RESTfulchemyTests(unittest.TestCase):

    """A collection of RESTfulchemy tests."""

    def setUp(self):
        """Configure a db session for the chinook database."""
        connect_string = "sqlite+pysqlite:///" + os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "chinook.sqlite")
        self.db_engine = create_engine(connect_string)
        self.DBSession = sessionmaker(bind=self.db_engine)
        self.db_session = self.DBSession()

    def test_db(self):
        """Make sure our test db is functional."""
        result = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()
        self.assertTrue(len(result) == 1 and result[0].artist_id == 1)

    def test_simple_update(self):
        """Make sure that a simple obj update works."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        update_resource(self.db_session, album, {"title": "TEST"})
        self.assertTrue(album.title == "TEST")

    def test_null_update(self):
        """Make sure that a obj update works with no update params."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        update_resource(self.db_session, album, None)
        self.assertTrue(
            album.album_id == 1 and
            album.title == "For Those About To Rock We Salute You" and
            album.artist_id == 1)

    def test_list_relation_new(self):
        """Make sure that we can add to a list using relationship."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).all()[0]
        update_dict = {
            "tracks.$new0.$add": "True",
            "tracks.$new0.track_id": "4000",
            "tracks.$new0.name": "Test Track Seven",
            "tracks.$new0.album_id": "347",
            "tracks.$new0.media_type_id": "2",
            "tracks.$new0.genre_id": "10",
            "tracks.$new0.composer": "Nick Repole",
            "tracks.$new0.milliseconds": "206009",
            "tracks.$new0.bytes": "3305166",
            "tracks.$new0.unit_price": "0.99",
        }
        update_resource(
            self.db_session,
            playlist,
            update_dict)
        self.assertTrue(len(playlist.tracks) == 2 and
                        playlist.tracks[1].composer == "Nick Repole")

    def test_list_relation_new_whitelist(self):
        """Make sure whitelisting is working for list relations."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).all()[0]
        update_dict = {
            "tracks.$new0.$add": "True",
            "tracks.$new0.track_id": "4000",
            "tracks.$new0.name": "Test Track Seven",
            "tracks.$new0.album_id": "347",
            "tracks.$new0.media_type_id": "2",
            "tracks.$new0.genre_id": "10",
            "tracks.$new0.composer": "Nick Repole",
            "tracks.$new0.milliseconds": "206009",
            "tracks.$new0.bytes": "3305166",
            "tracks.$new0.unit_price": "0.99",
        }
        update_resource(
            self.db_session,
            playlist,
            update_dict,
            ["tracks.$create",
             "tracks.$add",
             "tracks.track_id",
             "tracks.name",
             "tracks.album_id",
             "tracks.media_type_id",
             "tracks.genre_id",
             "tracks.composer",
             "tracks.milliseconds",
             "tracks.bytes",
             "tracks.unit_price"]
        )
        self.assertTrue(len(playlist.tracks) == 2 and
                        playlist.tracks[1].composer == "Nick Repole")

    def test_list_relation_new_generic_whitelist(self):
        """Make sure generic whitelisting works for list relations."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).all()[0]
        update_dict = {
            "tracks.$new0.$add": "True",
            "tracks.$new0.track_id": "4000",
            "tracks.$new0.name": "Test Track Seven",
            "tracks.$new0.album_id": "347",
            "tracks.$new0.media_type_id": "2",
            "tracks.$new0.genre_id": "10",
            "tracks.$new0.composer": "Nick Repole",
            "tracks.$new0.milliseconds": "206009",
            "tracks.$new0.bytes": "3305166",
            "tracks.$new0.unit_price": "0.99",
        }
        update_resource(
            self.db_session,
            playlist,
            update_dict,
            ["tracks",
             "tracks.track_id",
             "tracks.name",
             "tracks.album_id",
             "tracks.media_type_id",
             "tracks.genre_id",
             "tracks.composer",
             "tracks.milliseconds",
             "tracks.bytes",
             "tracks.unit_price"]
        )
        self.assertTrue(len(playlist.tracks) == 2 and
                        playlist.tracks[1].composer == "Nick Repole")

    def test_list_relation_new_whitelist_fail(self):
        """Make sure whitelisting properly fails for list relations."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).all()[0]
        update_dict = {
            "tracks.$new0.$add": "True",
            "tracks.$new0.track_id": "4000",
            "tracks.$new0.name": "Test Track Seven",
            "tracks.$new0.album_id": "347",
            "tracks.$new0.media_type_id": "2",
            "tracks.$new0.genre_id": "10",
            "tracks.$new0.composer": "Nick Repole",
            "tracks.$new0.milliseconds": "206009",
            "tracks.$new0.bytes": "3305166",
            "tracks.$new0.unit_price": "0.99",
        }
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            playlist,
            update_dict,
            ["tracks.track_id",
             "tracks.name",
             "tracks.album_id",
             "tracks.media_type_id",
             "tracks.genre_id",
             "tracks.composer",
             "tracks.milliseconds",
             "tracks.bytes",
             "tracks.unit_price"]
        )

    def test_list_relation_add_item(self):
        """Make sure that we can add an item to a list relation."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).first()
        update_resource(
            self.db_session,
            playlist,
            {"tracks.$id:track_id=1.~add": True}
        )
        self.assertTrue(len(playlist.tracks) == 2)

    def test_list_relation_add_item_no_add_fail(self):
        """Make sure that we can add an item to a list relation."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).first()
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            playlist,
            {"tracks.$id:track_id=1.~add": False}
        )

    def test_list_relation_add_item_whitelist(self):
        """Make sure we can add an item to a whitelisted relation."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).first()
        update_resource(
            self.db_session,
            playlist,
            {"tracks.$id:track_id=1.$add": True},
            ["tracks.$add"]
        )
        self.assertTrue(len(playlist.tracks) == 2)

    def test_list_relation_add_item_generic_whitelist(self):
        """Ensure generic whitelisting works for updating a relation."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).first()
        update_resource(
            self.db_session,
            playlist,
            {"tracks.$id:track_id=1.$add": True},
            ["tracks"]
        )
        self.assertTrue(len(playlist.tracks) == 2)

    def test_list_relation_add_item_whitelist_fail(self):
        """Ensure whitelisting rightly fails for updating a relation."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).first()
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            playlist,
            {"tracks.$id:track_id=1.$add": True},
            []
        )

    def test_list_relation_update_item(self):
        """Ensure we can update a list relationship item."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).first()
        update_resource(
            self.db_session,
            playlist,
            {"tracks.$id:track_id=597.name": "Test Track Seven"})
        self.assertTrue(playlist.tracks[0].name == "Test Track Seven")

    def test_list_relation_update_item_whitelist(self):
        """Ensure we can update a whitelisted list relationship item."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).first()
        update_resource(
            self.db_session,
            playlist,
            {"tracks.$id:track_id=597.name": "Test Track Seven"},
            ["tracks.name"])
        self.assertTrue(playlist.tracks[0].name == "Test Track Seven")

    def test_list_relation_remove_item(self):
        """Make sure that we can remove an item from a list relation."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).first()
        update_resource(
            self.db_session,
            playlist,
            {"tracks.$id:track_id=597.$remove": True}
        )
        self.assertTrue(len(playlist.tracks) == 0)

    def test_list_relation_remove_item_whitelist(self):
        """Make sure we can remove an item in a whitelisted relation."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).first()
        update_resource(
            self.db_session,
            playlist,
            {"tracks.$id:track_id=597.$remove": True},
            ["tracks.$remove"]
        )
        self.assertTrue(len(playlist.tracks) == 0)

    def test_list_relation_remove_item_generic_whitelist(self):
        """Ensure generic whitelisting works for deleting a relation."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).first()
        update_resource(
            self.db_session,
            playlist,
            {"tracks.$id:track_id=597.$remove": True},
            ["tracks"]
        )
        self.assertTrue(len(playlist.tracks) == 0)

    def test_list_relation_remove_item_whitelist_fail(self):
        """Ensure whitelisting rightly fails for deleting a relation."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).first()
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            playlist,
            {"tracks.$id:track_id=597.$remove": True},
            []
        )

    def test_single_relation_item(self):
        """Make sure that a non-list relation can have a field set."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        update_resource(
            self.db_session,
            album,
            {"artist.$id:artist_id=1.name": "TEST"})
        self.assertTrue(album.artist.name == "TEST")

    def test_single_relation_item_no_id_fail(self):
        """Ensure we can't set a non list relation field with no id."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            album,
            {"artist.name": "TEST"})

    def test_single_relation_item_bad_id_fail(self):
        """Ensure an invalid $id errors as expected."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            album,
            {"artist.$id:ardtist_id=1.name": "TEST"})

    def test_single_relation_item_set_fail(self):
        """Ensure we can't set an id relation to a non object value."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            album,
            {"artist.$id:artist_id=1": "TEST"})

    def test_set_single_relation_item(self):
        """Make sure that a non-list relation can be set."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        update_resource(
            self.db_session,
            album,
            {"artist.$id:artist_id=3.$set": True})
        self.assertTrue(album.artist.name == "Aerosmith")

    def test_set_empty_single_relation_item(self):
        """Make sure that an empty non-list relation can be set."""
        track = self.db_session.query(models.Track).filter(
            models.Track.track_id == 1).all()[0]
        track.genre = None
        update_resource(
            self.db_session,
            track,
            {"genre.$id:genre_id=1.$set": True})
        self.assertTrue(track.genre.name == "Rock")

    def test_set_empty_single_relation_item_no_set_fail(self):
        """Ensure no .$set causes failure on null non list relation."""
        employee = self.db_session.query(models.Employee).filter(
            models.Employee.employee_id == 1).first()
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            employee,
            {"parent.$id:employee_id=5.$set": False})

    def test_set_single_relation_item_no_set_fail(self):
        """Ensure no .$set causes a failure on non list relation."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            album,
            {"artist.$id:artist_id=3.$set": False})

    def test_set_single_relation_item_whitelist(self):
        """Make sure a whitelisted non-list relation can be set."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        update_resource(
            self.db_session,
            album,
            {"artist.$id:artist_id=3.$set": True},
            ["artist.~set"])
        self.assertTrue(album.artist.name == "Aerosmith")

    def test_set_single_relation_item_generic_whitelist(self):
        """Ensure a generic whitelist works for a non-list relation."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        update_resource(
            self.db_session,
            album,
            {"artist.$id:artist_id=3.$set": True},
            ["artist"])
        self.assertTrue(album.artist.name == "Aerosmith")

    def test_set_single_relation_item_whitelist_fail(self):
        """Ensure setting non whitelisted single relation items fail."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            album,
            {"artist.$id:artist_id=3.$set": True},
            [])

    def test_set_empty_single_relation_item_whitelist_fail(self):
        """Ensure setting empty non whitelisted relation item fails."""
        employee = self.db_session.query(models.Employee).filter(
            models.Employee.employee_id == 1).first()
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            employee,
            {"parent.$id:employee_id=5.$set": True},
            [])

    def test_new_single_relation_item(self):
        """Make sure that a non-list relation can be created."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        update_resource(
            self.db_session,
            album,
            {
                "artist.$new.$set": True,
                "artist.$new.name": "Nick Repole",
            })
        self.assertTrue(album.artist.name == "Nick Repole")

    def test_new_single_relation_item_whitelist(self):
        """Make sure a whitelisted non-list relation can be set."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        update_resource(
            self.db_session,
            album,
            {
                "artist.$new.$set": True,
                "artist.$new.name": "Nick Repole",
            },
            ["artist.$create", "artist.$set"])
        self.assertTrue(album.artist.name == "Nick Repole")

    def test_new_single_relation_item_generic_whitelist(self):
        """Ensure a generic whitelist works for a non-list relation."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        update_resource(
            self.db_session,
            album,
            {
                "artist.$new.$set": True,
                "artist.$new.name": "Nick Repole",
            },
            ["artist"])
        self.assertTrue(album.artist.name == "Nick Repole")

    def test_new_single_relation_item_whitelist_fail(self):
        """Ensure a non-whitelisted new non-list relation fails."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            album,
            {
                "artist.$new.$set": True,
                "artist.$new.name": "Nick Repole",
            },
            ["artist.name"])

    def test_invalid_new_parent(self):
        """Make sure that $new errors when parent isn't relationship."""
        album = self.db_session.query(AlbumPlus).filter(
            AlbumPlus.album_id == 1).all()[0]
        self.assertRaises(
            AttributeError,
            update_resource,
            self.db_session,
            album,
            {
                "test.$new.$add": True
            })

    def test_invalid_new_parent_column(self):
        """Make sure that $new errors when parent is a column prop."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        self.assertRaises(
            TypeError,
            update_resource,
            self.db_session,
            album,
            {
                "album_id.$new.$add": True
            })

    def test_invalid_set_relation_parent(self):
        """Make sure that $id errors when parent isn't relationship."""
        album = self.db_session.query(AlbumPlus).filter(
            AlbumPlus.album_id == 1).all()[0]
        self.assertRaises(
            AttributeError,
            update_resource,
            self.db_session,
            album,
            {
                "test.$id:artist_id=1.$add": True
            })

    def test_invalid_set_relation_parent_column(self):
        """Make sure that $id errors when parent is a column prop."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        self.assertRaises(
            TypeError,
            update_resource,
            self.db_session,
            album,
            {
                "album_id.$id:artist_id=1.$add": True
            })

    def test_invalid_remove(self):
        """Make sure that a %remove on a non relation item errors."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        self.assertRaises(
            TypeError,
            update_resource,
            self.db_session,
            album,
            {
                "album_id.$remove": True
            })

    def test_invalid_set_obj_to_raw_value(self):
        """Make sure we can't set a relationship to a raw value."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            album,
            {
                "artist": 5
            })

    def test_remove_single_relation_item(self):
        """Make sure a non-list relation can be removed."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        update_resource(
            self.db_session,
            album,
            {"artist.$id:artist_id=1.$remove": True})
        self.assertTrue(album.artist is None)

    def test_remove_single_relation_item_bad_id(self):
        """Make sure a non matching $id can't be removed."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            album,
            {"artist.$id:artist_id=3.$remove": True})

    def test_remove_single_relation_item_whitelist(self):
        """Make sure a whitelisted non-list relation can be removed."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        update_resource(
            self.db_session,
            album,
            {"artist.$id:artist_id=1.$remove": True},
            ["artist.$remove"])
        self.assertTrue(album.artist is None)

    def test_remove_single_relation_item_generic_whitelist(self):
        """Ensure generic whitelisted non-list relation is deletable."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        update_resource(
            self.db_session,
            album,
            {"artist.$id:artist_id=1.$remove": True},
            ["artist"])
        self.assertTrue(album.artist is None)

    def test_remove_single_relation_item_whitelist_fail(self):
        """Ensure invalid whitelist fails to remove single relation."""
        album = self.db_session.query(models.Album).filter(
            models.Album.album_id == 1).all()[0]
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            album,
            {"artist.$id:artist_id=1.$remove": True},
            ["artist.name"])

    def test_get_class_attributes_invalid_start_fail(self):
        """Ensure get_class_attributes fails - no leading class name."""
        self.assertRaises(
            AttributeError,
            restfulchemy.get_class_attributes,
            models.Playlist,
            "invalid_attr_name")

    def test_get_class_attributes_invalid_attr_fail(self):
        """Ensure get_class_attributes fails - no such attr in model."""
        self.assertRaises(
            AttributeError,
            restfulchemy.get_class_attributes,
            models.Playlist,
            "Playlist.invalid_attr_name")

    def test_simple_create(self):
        """Make sure we can create a new instance of a model."""
        album = create_resource(
            self.db_session,
            models.Album,
            {"title": "Test Album",
             "artist_id": 1}
        )
        self.assertTrue(album.title == "Test Album")

    def test_stack_size_limit(self):
        """Make sure that limiting the stack size works as expected."""
        playlist = self.db_session.query(models.Playlist).filter(
            models.Playlist.playlist_id == 18).all()[0]
        update_dict = {
            "tracks.$new0.$add": "True",
            "tracks.$new0.track_id": "4000",
            "tracks.$new0.name": "Test Track Seven",
            "tracks.$new0.album_id": "347",
            "tracks.$new0.media_type_id": "2",
            "tracks.$new0.genre_id": "10",
            "tracks.$new0.composer": "Nick Repole",
            "tracks.$new0.milliseconds": "206009",
            "tracks.$new0.bytes": "3305166",
            "tracks.$new0.unit_price": "0.99",
        }
        update_resource(
            self.db_session,
            playlist,
            update_dict,
            stack_size_limit=100)
        self.assertTrue(len(playlist.tracks) == 2 and
                        playlist.tracks[1].composer == "Nick Repole")
        self.assertRaises(
            AlchemyUpdateException,
            update_resource,
            self.db_session,
            playlist,
            update_dict,
            stack_size_limit=1)

    def test_get_resources(self):
        """Test simple get_resources functionality."""
        query_params = {
            "album_id_$lt": "10",
            "$query": json.dumps({"title": "Big Ones"})
        }
        result = get_resources(
            self.db_session,
            models.Album,
            query_params)
        self.assertTrue(
            len(result) == 1 and
            result[0].album_id == 5
        )

    def test_get_resources_filters(self):
        """Test simple get_resources filtering functionality."""
        query_params = {
            "album_id_$lt": "10",
            "title_$like": "Big",
            "album_id_$gt": 4,
            "album_id_$gte": 5,
            "album_id_$lte": 5,
            "album_id_$eq": 5,
            "album_id": 5,
            "album_id_$ne": 6,
            "$query": json.dumps({"title": "Big Ones"})
        }
        result = get_resources(
            self.db_session,
            models.Album,
            query_params)
        self.assertTrue(
            len(result) == 1 and
            result[0].album_id == 5
        )

    def test_get_all_objects(self):
        """Test getting all objects with an empty dict of params."""
        query_params = {}
        result = get_resources(
            self.db_session,
            models.Album,
            query_params)
        self.assertTrue(len(result) == 347)

    def test_get_all_objects_null_query(self):
        """Test getting all objects with query_params set to `None`."""
        query_params = None
        result = get_resources(
            self.db_session,
            models.Album,
            query_params)
        self.assertTrue(len(result) == 347)

    def test_get_resource(self):
        """Test simple get_resource functionality."""
        query_params = {
            "album_id_$lt": "10",
            "$query": json.dumps({"title": "Big Ones"})
        }
        result = get_resource(
            self.db_session,
            models.Album,
            query_params)
        self.assertTrue(result.album_id == 5)

    def test_get_resource_list_param(self):
        """Test get_resource functionality with list query params."""
        query_params = {
            "album_id_$lt": ["10", "6"],
            "$query": [json.dumps({"title": "Big Ones"}),
                       json.dumps({"album_id": "5"})]
        }
        result = get_resource(
            self.db_session,
            models.Album,
            query_params)
        self.assertTrue(result.album_id == 5)

    def test_get_resource_bad_query(self):
        """Ensure get_resource fails when passed bad query parameters."""
        query_params = {
            "$query": json.dumps(["Big Ones"])
        }
        self.assertRaises(
            InvalidMQLException,
            get_resource,
            self.db_session,
            models.Album,
            query_params)

    def test_get_resources_ordered(self):
        """Test simple get_resources ~order_by functionality."""
        query_params = {
            "~order_by": "album_id~DESC-title~ASC"
        }
        result = get_resources(
            self.db_session,
            models.Album,
            query_params)
        self.assertTrue(
            len(result) > 0 and
            result[0].album_id == 347
        )

    def test_get_first_page(self):
        """Test that we can get the first page of a set of objects."""
        query_params = {
            "~order_by": "album_id~ASC"
        }
        result = get_resources(
            self.db_session,
            models.Album,
            query_params,
            page=1,
            page_max_size=30)
        self.assertTrue(
            len(result) == 30 and
            result[0].album_id == 1)

    def test_get_second_page(self):
        """Test that we can get the second page of a set of objects."""
        query_params = {}
        result = get_resources(
            self.db_session,
            models.Album,
            query_params,
            page=2,
            page_max_size=30)
        self.assertTrue(
            len(result) == 30 and
            result[0].album_id == 31)

    def test_no_page_max_size_fail(self):
        """Not providing a max page size with page > 1 should fail."""
        query_params = {
            "~order_by": "album_id~ASC"
        }
        self.assertRaises(
            ValueError,
            get_resources,
            self.db_session,
            models.Album,
            query_params,
            page=2)

    def test_bad_page_num(self):
        """Not providing a max page size with page > 1 should fail."""
        query_params = {}
        self.assertRaises(
            ValueError,
            get_resources,
            self.db_session,
            models.Album,
            query_params,
            page=-1)

    def test_offset(self):
        """Make sure providing an offset query_param works."""
        query_params = {
            "~offset": "1"
        }
        result = get_resources(
            self.db_session,
            models.Album,
            query_params)
        self.assertTrue(
            result[0].album_id == 2
        )

    def test_offset_fail(self):
        """Make sure providing a bad offset query_param is ignored."""
        query_params = {
            "~offset": "dafd"
        }
        result = get_resources(
            self.db_session,
            models.Album,
            query_params)
        self.assertTrue(len(result) == 347)

    def test_limit(self):
        """Make sure providing a limit query_param works."""
        query_params = {
            "~limit": "1"
        }
        result = get_resources(
            self.db_session,
            models.Album,
            query_params)
        self.assertTrue(len(result) == 1)

    def test_limit_fail(self):
        """Make sure providing a bad limit query_param is ignored."""
        query_params = {
            "~limit": "dafd"
        }
        result = get_resources(
            self.db_session,
            models.Album,
            query_params)
        self.assertTrue(len(result) == 347)

    def test_limit_override(self):
        """Ensure providing a page_max_size overrides a high limit."""
        query_params = {
            "~limit": "100"
        }
        result = get_resources(
            self.db_session,
            models.Album,
            query_params,
            page_max_size=30)
        self.assertTrue(len(result) == 30)

if __name__ == '__main__':    # pragma: no cover
    unittest.main()
