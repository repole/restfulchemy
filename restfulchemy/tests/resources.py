from restfulchemy.resource import ModelResource
from restfulchemy.tests.schemas import *


class AlbumResource(ModelResource):
    class Meta:
        schema_class = AlbumSchema


class InvoiceLineResource(ModelResource):
    class Meta:
        schema_class = InvoiceLineSchema


class InvoiceResource(ModelResource):
    class Meta:
        schema_class = InvoiceSchema


class EmployeeResource(ModelResource):
    class Meta:
        schema_class = EmployeeSchema


class CustomerResource(ModelResource):
    class Meta:
        schema_class = CustomerSchema


class PlaylistResource(ModelResource):
    class Meta:
        schema_class = PlaylistSchema


class MediaTypeResource(ModelResource):
    class Meta:
        schema_class = MediaTypeSchema


class GenreResource(ModelResource):
    class Meta:
        schema_class = GenreSchema


class TrackResource(ModelResource):
    class Meta:
        schema_class = TrackSchema


class ArtistResource(ModelResource):
    class Meta:
        schema_class = ArtistSchema
