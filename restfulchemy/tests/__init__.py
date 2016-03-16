## -*- coding: utf-8 -*-\
"""
    restfulchemy.tests.__init__
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests for RESTfulchemy.

    :copyright: (c) 2016 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
import unittest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mqlalchemy import InvalidMQLException
from mqlalchemy.utils import dummy_gettext
from restfulchemy.resource import UnprocessableEntityError
from restfulchemy.tests.resources import *
from restfulchemy.parser import (
    parse_filters, parse_offset_limit, parse_sorts, parse_embeds, parse_fields,
    OffsetLimitParseError)
import json
import tempfile
import shutil


class RESTfulchemyTests(unittest.TestCase):

    """A collection of RESTfulchemy tests."""

    def setUp(self):
        """Configure a db session for the chinook database."""
        self.temp_user_data_path = tempfile.mkdtemp()
        db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "chinook.sqlite")
        shutil.copy(db_path, self.temp_user_data_path)
        db_path = os.path.join(self.temp_user_data_path, "chinook.sqlite")
        connect_string = "sqlite+pysqlite:///" + db_path
        self.db_engine = create_engine(connect_string)
        self.DBSession = sessionmaker(bind=self.db_engine)
        self.db_session = self.DBSession()

    def tearDown(self):
        self.db_session.expunge_all()
        self.db_session.rollback()

    def test_db(self):
        """Make sure our test db is functional."""
        result = self.db_session.query(Album).filter(
            Album.album_id == 1).all()
        self.assertTrue(len(result) == 1 and result[0].artist_id == 1)

    def test_simple_patch(self):
        """Make sure that a simple obj update works."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(db_session=self.db_session)
        result = album_resource.patch((album.album_id,), {"title": "TEST"})
        self.assertTrue(
            result["title"] == "TEST" and
            album.title == "TEST")

    def test_empty_patch(self):
        """Make sure that a obj update works with no update params."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(db_session=self.db_session)
        result = album_resource.patch((album.album_id,), {})
        self.assertTrue(
            result["title"] == album.title)

    def test_list_relation_add_item(self):
        """Make sure that we can add an item to a list relation."""
        playlist = self.db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).first()
        self.assertTrue(len(playlist.tracks) == 1)
        playlist_resource = PlaylistResource(db_session=self.db_session)
        update_data = {
            "tracks": [{
                "$op": "add",
                "track_id": "1"
            }]
        }
        result = playlist_resource.patch((playlist.playlist_id,), update_data)
        self.assertTrue(
            len(playlist.tracks) == 2 and
            len(result["tracks"]) == 2)

    def test_list_relation_add_new_item(self):
        """Ensure we can add a new obj to a list using relationship."""
        playlist = self.db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).all()[0]
        update_data = {
            "tracks": [{
                "$op": "add",
                "track_id": "4000",
                "name": "Test Track Seven",
                "album": {
                    "album_id": "347",
                },
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                   "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            }]
        }
        playlist_resource = PlaylistResource(db_session=self.db_session)
        result = playlist_resource.patch((playlist.playlist_id,), update_data)
        self.assertTrue(len(playlist.tracks) == 2 and
                        len(result["tracks"]) == 2 and
                        playlist.tracks[1].composer == "Nick Repole" and
                        result["tracks"][1]["composer"] == "Nick Repole")

    def test_list_relation_update_item(self):
        """Ensure we can update a list relationship item."""
        playlist = self.db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).first()
        playlist_resource = PlaylistResource(db_session=self.db_session)
        update_data = {
            "tracks": [{
                "track_id": 597,
                "name": "Test Track Seven"
            }]
        }
        result = playlist_resource.patch((playlist.playlist_id,), update_data)
        self.assertTrue(
            playlist.tracks[0].name == "Test Track Seven" and
            result["tracks"][0]["name"] == playlist.tracks[0].name)

    def test_single_relation_item(self):
        """Make sure that a non-list relation can have a field set."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        update_data = {
            "artist": {"name": "TEST"}
        }
        album_resource = AlbumResource(db_session=self.db_session)
        result = album_resource.patch((album.album_id,), update_data)
        self.assertTrue(
            album.artist.name == "TEST" and
            result["artist"]["name"] == album.artist.name)

    def test_single_relation_item_set_fail(self):
        """Ensure we can't set a relation to a non object value."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(db_session=self.db_session)
        self.assertRaises(
            UnprocessableEntityError,
            album_resource.patch,
            (album.album_id, ),
            {"artist": "TEST"})

    def test_list_relation_set_fail(self):
        """Ensure we can't set a list relation to a non object value."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(db_session=self.db_session)
        self.assertRaises(
            UnprocessableEntityError,
            album_resource.patch,
            (album.album_id, ),
            {"tracks": "TEST"})

    def test_list_relation_non_item_fail(self):
        """Ensure we can't set list relation items to a non object."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(db_session=self.db_session)
        self.assertRaises(
            UnprocessableEntityError,
            album_resource.patch,
            (album.album_id, ),
            {"tracks": ["TEST"]})

    def test_list_relation_bad_item_value_fail(self):
        """Ensure list relation item validation works."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(db_session=self.db_session)
        self.assertRaises(
            UnprocessableEntityError,
            album_resource.patch,
            (album.album_id, ),
            {"tracks": [{"bytes": "TEST"}]})

    def test_error_translation(self):
        """Ensure error message translation works."""
        def getexcited(value, **variables):
            """Append an exclamation point to any string."""
            return dummy_gettext(value, **variables) + "!"
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(db_session=self.db_session,
                                       gettext=getexcited)
        try:
            album_resource.patch(
                (album.album_id, ), {"tracks": [{"bytes": "TEST"}]})
            # should raise an exception...
            self.assertTrue(False)
        except UnprocessableEntityError as e:
            self.assertTrue(e.args[0]['tracks'][0]['name'][0].endswith("!"))

    def test_set_single_relation_item(self):
        """Make sure that a non-list relation can be set."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(db_session=self.db_session)
        update_params = {
            "artist": {"artist_id": 3}
        }
        result = album_resource.patch((album.album_id,), update_params)
        self.assertTrue(
            album.artist.name == "Aerosmith" and
            result["artist"]["name"] == album.artist.name)

    def test_set_single_relation_item_to_none(self):
        """Make sure that a non-list relation can be set to `None`."""
        track = self.db_session.query(Track).filter(
            Track.track_id == 1).all()[0]
        track_resource = TrackResource(db_session=self.db_session)
        update_params = {
            "genre": None
        }
        result = track_resource.patch((track.track_id,), update_params)
        self.assertTrue(
            track.genre is None and
            result["genre"] is None)

    def test_set_empty_single_relation_item(self):
        """Make sure that an empty non-list relation can be set."""
        track = self.db_session.query(Track).filter(
            Track.track_id == 1).all()[0]
        track.genre = None
        track_resource = TrackResource(db_session=self.db_session)
        update_data = {
            "genre": {"genre_id": 1}
        }
        result = track_resource.patch((track.track_id, ), update_data)
        self.assertTrue(
            track.genre.name == "Rock" and
            result["genre"]["name"] == track.genre.name)

    def test_list_relation_remove_item(self):
        """Make sure that we can remove an item from a list relation."""
        playlist = self.db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).first()
        playlist_resource = PlaylistResource(db_session=self.db_session)
        update_params = {
            "tracks": [{
                "track_id": 597,
                "$op": "remove"
            }]
        }
        result = playlist_resource.patch(
            (playlist.playlist_id, ), update_params)
        self.assertTrue(
            len(playlist.tracks) == 0 and
            len(result["tracks"]) == 0)

    def test_new_single_relation_item(self):
        """Make sure that a non-list relation can be created."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).first()
        album_resource = AlbumResource(db_session=self.db_session)
        update_params = {
            "artist": {
                "artist_id": 999,
                "name": "Nick Repole",
            }
        }
        result = album_resource.patch((album.album_id,), update_params)
        # make sure original artist wasn't just edited.
        artist = self.db_session.query(Artist).filter(
            Artist.artist_id == 1).first()
        self.assertTrue(
            album.artist.name == "Nick Repole" and
            result["artist"]["name"] == album.artist.name and
            artist is not None)

    def test_get_collection(self):
        """Test simple get_collection functionality."""
        query_params = {
            "album_id-lt": "10",
            "query": json.dumps({"title": "Big Ones"})
        }
        album_resource = AlbumResource(db_session=self.db_session)
        result = album_resource.get_collection(
            filters=parse_filters(album_resource.model, query_params)
        )
        self.assertTrue(
            len(result) == 1 and
            result[0]["album_id"] == 5
        )

    def test_get_collection_filters(self):
        """Test simple get_collection filtering functionality."""
        query_params = {
            "album_id-lt": "10",
            "title-like": "Big",
            "album_id-gt": 4,
            "album_id-gte": 5,
            "album_id-lte": 5,
            "album_id-eq": 5,
            "album_id": 5,
            "album_id-ne": 6,
            "query": json.dumps({"title": "Big Ones"})
        }
        album_resource = AlbumResource(db_session=self.db_session)
        result = album_resource.get_collection(
            filters=parse_filters(album_resource.model, query_params)
        )
        self.assertTrue(
            len(result) == 1 and
            result[0]["album_id"] == 5
        )

    def test_get_all_objects(self):
        """Test getting all objects with an empty dict of params."""
        query_params = {}
        album_resource = AlbumResource(db_session=self.db_session)
        result = album_resource.get_collection(
            filters=parse_filters(album_resource.model, query_params)
        )
        self.assertTrue(len(result) == 347)

    def test_get_all_objects_null_query(self):
        """Test getting all objects with query_params set to `None`."""
        query_params = None
        album_resource = AlbumResource(db_session=self.db_session)
        result = album_resource.get_collection(
            filters=parse_filters(album_resource.model, query_params)
        )
        self.assertTrue(len(result) == 347)

    def test_get_resources_ordered(self):
        """Test simple get_resources sort functionality."""
        query_params = {
            "sort": "-album_id,title"
        }
        album_resource = AlbumResource(db_session=self.db_session)
        result = album_resource.get_collection(
            filters=parse_filters(album_resource.model, query_params),
            sorts=parse_sorts(query_params)
        )
        self.assertTrue(
            len(result) == 347 and
            result[0]["album_id"] == 347)

    def test_get_first_page(self):
        """Test that we can get the first page of a set of objects."""
        query_params = {
            "sort": "album_id"
        }
        album_resource = AlbumResource(db_session=self.db_session)
        offset, limit = parse_offset_limit(query_params, page_max_size=30)
        result = album_resource.get_collection(
            filters=parse_filters(album_resource.model, query_params),
            sorts=parse_sorts(query_params),
            limit=limit,
            offset=offset
        )
        self.assertTrue(
            len(result) == 30 and
            result[0]["album_id"] == 1)

    def test_get_second_page(self):
        """Test that we can get the second page of a set of objects."""
        query_params = {
            "sort": "album_id",
            "page": "2"
        }
        album_resource = AlbumResource(db_session=self.db_session)
        offset, limit = parse_offset_limit(query_params, page_max_size=30)
        result = album_resource.get_collection(
            filters=parse_filters(album_resource.model, query_params),
            sorts=parse_sorts(query_params),
            limit=limit,
            offset=offset
        )
        self.assertTrue(
            len(result) == 30 and
            result[0]["album_id"] == 31)

    def test_no_page_max_size_fail(self):
        """Not providing a max page size with page > 1 should fail."""
        query_params = {"page": "2"}
        self.assertRaises(
            OffsetLimitParseError,
            parse_offset_limit,
            query_params
        )

    def test_bad_page_num(self):
        """Test that providing a negative page number fails."""
        query_params = {"page": "-1"}
        self.assertRaises(
            OffsetLimitParseError,
            parse_offset_limit,
            query_params
        )

    def test_offset(self):
        """Make sure providing an offset query_param works."""
        query_params = {
            "offset": "1"
        }
        album_resource = AlbumResource(db_session=self.db_session)
        offset, limit = parse_offset_limit(query_params, page_max_size=30)
        result = album_resource.get_collection(
            filters=parse_filters(album_resource.model, query_params),
            sorts=parse_sorts(query_params),
            limit=limit,
            offset=offset
        )
        self.assertTrue(result[0]["album_id"] == 2)

    def test_offset_fail(self):
        """Make sure providing a bad offset query_param is ignored."""
        query_params = {"offset": "abcd"}
        self.assertRaises(
            OffsetLimitParseError,
            parse_offset_limit,
            query_params
        )

    def test_limit(self):
        """Make sure providing a limit query_param works."""
        query_params = {
            "limit": "1"
        }
        album_resource = AlbumResource(db_session=self.db_session)
        offset, limit = parse_offset_limit(query_params, page_max_size=30)
        result = album_resource.get_collection(
            filters=parse_filters(album_resource.model, query_params),
            sorts=parse_sorts(query_params),
            limit=limit,
            offset=offset
        )
        self.assertTrue(len(result) == 1)

    def test_limit_fail(self):
        """Make sure providing a bad limit query_param is ignored."""
        query_params = {"limit": "abcd"}
        self.assertRaises(
            OffsetLimitParseError,
            parse_offset_limit,
            query_params
        )

    def test_limit_override(self):
        """Ensure providing a page_max_size overrides a high limit."""
        query_params = {"limit": "1000"}
        self.assertRaises(
            OffsetLimitParseError,
            parse_offset_limit,
            query_params,
            30
        )

if __name__ == '__main__':    # pragma: no cover
    unittest.main()
