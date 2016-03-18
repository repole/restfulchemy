"""
    restfulchemy.schema
    ~~~~~~~~~~~~~~~~~~~

    Classes for building REST API friendly, model based schemas.

    :copyright: (c) 2016 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from inflection import camelize, pluralize
from marshmallow.base import FieldABC, SchemaABC
from marshmallow_sqlalchemy.fields import get_primary_keys
from marshmallow_sqlalchemy.schema import ModelSchema, ModelSchemaOpts
from mqlalchemy.utils import dummy_gettext
from restfulchemy.convert import ModelResourceConverter
from restfulchemy.fields import EmbeddedField


class ModelResourceSchemaOpts(ModelSchemaOpts):
    """Meta class options for use with a `ModelResourceSchema`.

    Defaults ``model_converter`` to
    :class:`~restfulchemy.convert.ModelResourceConverter`.

    Defaults ``id_keys`` to `None`, resulting in the model's
    primary keys being used as identifier fields.

    Example usage:

    .. code-block:: python

        class UserSchema(ModelResourceSchema):
            class Meta:
                # Use username to identify a user resource
                # rather than user_id.
                id_keys = ["username"]
                # Alternate converter to dump/load with camel case.
                model_converter = CamelModelResourceConverter

    """

    def __init__(self, meta):
        """Handle the meta class attached to a `ModelResourceSchema`.

        :param meta: The meta class attached to a
            :class:`~restfulchemy.schema.ModelResourceSchema`.

        """
        super(ModelResourceSchemaOpts, self).__init__(meta)
        self.id_keys = getattr(meta, 'id_keys', None)
        self.model_converter = getattr(
            meta, 'model_converter', ModelResourceConverter)


class ModelResourceSchema(ModelSchema):
    """Schema meant to be used with a `ModelResource`.

    Enables sub-resource embedding, context processing, error
    translation, and more.

    """

    OPTIONS_CLASS = ModelResourceSchemaOpts

    def __init__(self, *args, **kwargs):
        """Sets additional member vars on top of `ModelSchema`.

        Also runs :meth:`process_context` upon completion.

        :param gettext: Used to translate error messages.
        :type gettext: callable or None

        """
        self._gettext = kwargs.pop("gettext", None)
        super(ModelResourceSchema, self).__init__(*args, **kwargs)
        self.fields_by_dump_to = {}
        for key in self.fields:
            field = self.fields[key]
            if field.dump_to:
                self.fields_by_dump_to[field.dump_to] = field
            else:
                self.fields_by_dump_to[field.name] = field
        self.fields_by_load_from = {}
        for key in self.fields:
            field = self.fields[key]
            if field.load_from:
                self.fields_by_load_from[field.load_from] = field
            else:
                self.fields_by_load_from[field.name] = field
        self.process_context()

    def get_instance(self, data):
        """Retrieve an existing record by primary key(s).

        :param dict data: Data associated with this instance.

        """
        keys = self.id_keys
        filters = {
            key: data.get(key)
            for key in keys
        }
        if None not in filters.values():
            return self.session.query(
                self.opts.model
            ).filter_by(
                **filters
            ).first()
        return None

    def embed(self, items):
        """Embed the list of field names provided.

        :param list items: A list of embeddable sub resources or
            sub resource fields.

        """
        for item in items:
            split_names = item.split(".")
            parent = self
            for i, split_name in enumerate(split_names):
                if isinstance(parent, ModelSchema):
                    if isinstance(parent.fields.get(split_name, None),
                                  EmbeddedField):
                        field = parent.fields[split_name]
                        field.embed()
                        if hasattr(field.active_field, "process_context"):
                            field.active_field.process_context()
                        if hasattr(field.active_field, "schema"):
                            parent = field.active_field.schema
                        else:
                            parent = None
                    else:
                        if split_name in parent.fields:
                            parent.exclude = tuple()
                            if parent.only is None:
                                parent.only = tuple()
                            parent.only = parent.only + tuple([split_name])
                        else:
                            break

    @property
    def id_keys(self):
        """Get the fields used to identify a resource instance."""
        if (hasattr(self.opts, "id_keys") and
                isinstance(self.opts.id_keys, list)):
            return self.opts.id_keys
        else:
            return [col.key for col in get_primary_keys(self.opts.model)]

    @property
    def api_endpoint_base(self):
        """Get the api resource endpoint name for this resource."""
        schema_class_name = self.__class__.__name__
        result = schema_class_name
        if schema_class_name.endswith("Schema"):
            result = pluralize(schema_class_name[0:-len("Schema")])
            result = camelize(result, uppercase_first_letter=False)
            return result
        return camelize(pluralize(result), uppercase_first_letter=False)

    def load(self, data, session=None, instance=None, *args, **kwargs):
        """Deserialize the provided data into a SQLAlchemy object.

        :param dict data: Data to be loaded into an instance.
        :param session: Optional database session. Will be used in place
            of ``self.session`` if provided.
        :type session: :class:`~sqlalchemy.orm.session.Session`
        :param instance: SQLAlchemy model instance data should be loaded
            into. If `None` is provided at this point or when the
            class was initialized, an instance will either be determined
            using the provided data via :meth:`get_instance`, or if that
            fails a new instance will be created.
        :return: An instance with the provided data loaded into it.

        """
        for key in data:
            if (key in self.fields and
                    isinstance(self.fields[key], (EmbeddedField,))):
                self.embed([key])
        # make sure self.instance isn't None
        if instance is not None:
            self.instance = instance
        elif self.instance is None:
            self.instance = self.get_instance(data)
            if self.instance is None:
                self.instance = self.opts.model()
        return super(ModelResourceSchema, self).load(
             data, session, instance, *args, **kwargs)

    def handle_error(self, error, data):
        """Modifies error messages.

        :param error: The exception instance to be raised. The
            error messages are modified in place rather than a
            new error being created.
        :type error: :class:`~marshmallow.exceptions.ValidationError`
        :param dict data: The provided data to be deserialized.

        """
        messages = error.messages
        for key in messages:
            if isinstance(messages[key], list):
                for i in range(0, len(messages[key])):
                    messages[key][i] = self.translate_error(messages[key][i])

    def process_context(self):
        """Override to modify a schema based on context.

        Is called when a schema is initialized or embedded.

        """
        pass

    def translate_error(self, value, **variables):
        """Override to modify a schema based on context.

        :param str value: An error string to be translated.

        """
        if self._gettext is None:
            parent = self.root
            if isinstance(parent, FieldABC):
                if hasattr(parent, "root"):
                    parent = parent.root
            if isinstance(parent, SchemaABC):
                if hasattr(parent, "translate_error"):
                    return parent.translate_error(value, **variables)
        elif callable(self._gettext):
            return self._gettext(value, **variables)
        return dummy_gettext(value, **variables)