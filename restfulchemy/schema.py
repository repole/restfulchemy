from inflection import camelize, pluralize
from marshmallow_sqlalchemy.fields import get_primary_keys
from marshmallow_sqlalchemy.schema import ModelSchema, ModelSchemaOpts
from restfulchemy.convert import ModelResourceConverter
from restfulchemy.fields import EmbeddedField


class ModelResourceSchemaOpts(ModelSchemaOpts):
    """Simple options class for use with a `ModelResourceSchema`."""

    def __init__(self, meta):
        """Handle the meta class attached to a `ModelResourceSchema`."""
        super(ModelResourceSchemaOpts, self).__init__(meta)
        self.id_keys = getattr(meta, 'id_keys', None)
        self.model_converter = getattr(
            meta, 'model_converter', ModelResourceConverter)


class ModelResourceSchema(ModelSchema):
    """Schema meant to be used with the `ModelResource` class.

    Enables sub-resource embedding, context processing, and more.

    """

    OPTIONS_CLASS = ModelResourceSchemaOpts

    def __init__(self, *args, **kwargs):
        """Sets additional member vars on top of `ModelResource`.

        Also runs :meth:`process_context` upon completion.

        :param gettext: Used to translate error messages.

        """
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
        self.gettext = kwargs.pop("gettext", None)
        self.process_context()

    def get_instance(self, data):
        """Retrieve an existing record by primary key(s)."""
        # TODO - Check that data comes in already converted here.
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
        """Embed the list of field names provided."""
        for item in items:
            split_names = item.split(".")
            parent = self
            for i, split_name in enumerate(split_names):
                if isinstance(parent, ModelSchema):
                    if isinstance(parent.fields.get(split_name, None),
                                  EmbeddedField):
                        field = parent.fields[split_name]
                        field.embed()
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
        """Get the fields used to identify resource instances."""
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
        """Deserialize the provided data into a SQLAlchemy object."""
        for key in data:
            if (key in self.fields and
                    isinstance(self.fields[key], (EmbeddedField,))):
                self.fields[key].embed()
        if self.instance is None:
            self.instance = self.opts.model()
        return super(ModelResourceSchema, self).load(
             data, session, instance, *args, **kwargs)

    def handle_error(self, error, data):
        """TODO - Translate errors here."""
        pass

    def process_context(self):
        """Any sort of context handling should be done here."""
        pass
