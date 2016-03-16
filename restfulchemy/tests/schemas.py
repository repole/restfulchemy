"""
    restfulchemy.tests.schemas
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Schemas used for test purposes.

    :copyright: (c) 2016 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from mqlalchemy.tests.models import *
from restfulchemy.schema import ModelResourceSchema


class InvoiceLineSchema(ModelResourceSchema):
    class Meta:
        model = InvoiceLine


class InvoiceSchema(ModelResourceSchema):
    class Meta:
        model = Invoice


class EmployeeSchema(ModelResourceSchema):
    class Meta:
        model = Employee


class CustomerSchema(ModelResourceSchema):
    class Meta:
        model = Customer


class PlaylistSchema(ModelResourceSchema):
    class Meta:
        model = Playlist


class MediaTypeSchema(ModelResourceSchema):
    class Meta:
        model = MediaType


class GenreSchema(ModelResourceSchema):
    class Meta:
        model = Genre


class TrackSchema(ModelResourceSchema):
    class Meta:
        model = Track


class AlbumSchema(ModelResourceSchema):
    class Meta:
        model = Album


class ArtistSchema(ModelResourceSchema):
    class Meta:
        model = Artist
