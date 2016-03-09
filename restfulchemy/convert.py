from inflection import camelize
from marshmallow_sqlalchemy.convert import ModelConverter
from restfulchemy.fields import (EmbeddedField, NestedRelated, RelationshipUrl,
                                 APIUrl)


class ModelResourceConverter(ModelConverter):
    """Convert a model's fields for use in a `ModelResourceSchema`."""

    def _get_field_class_for_property(self, prop):
        if hasattr(prop, 'direction'):
            if prop.uselist:
                field_cls = EmbeddedField
            else:
                field_cls = EmbeddedField
        else:
            column = prop.columns[0]
            field_cls = self._get_field_class_for_column(column)
        return field_cls

    def _add_column_kwargs(self, kwargs, prop):
        """Add keyword arguments to kwargs (in-place) based on the passed in
        `Property`.
        """
        super(ModelResourceConverter, self)._add_column_kwargs(
                kwargs, prop.columns[0])

    def _add_relationship_kwargs(self, kwargs, prop):
        """Add keyword arguments to kwargs (in-place) based on the passed in
        relationship `Property`.
        """
        nullable = True
        for pair in prop.local_remote_pairs:
            if not pair[0].nullable:
                if prop.uselist is True:
                    nullable = False
                break
        if prop.uselist:
            default_field = RelationshipUrl(
                dump_only=True,
                resource=prop.mapper.class_.__name__ + 'Resource')
            embedded_field = NestedRelated(
                nested=prop.mapper.class_.__name__ + 'Schema',
                allow_none=nullable,
                many=prop.uselist
            )
            kwargs.update({
                'default_field': default_field,
                'embedded_field': embedded_field,
                'embedded': False
            })
        else:
            default_field = NestedRelated(
                nested=prop.mapper.class_.__name__ + 'Schema',
                allow_none=nullable,
                many=prop.uselist,
                only=("self", )
            )
            embedded_field = NestedRelated(
                nested=prop.mapper.class_.__name__ + 'Schema',
                allow_none=nullable,
                many=prop.uselist
            )
            kwargs.update({
                'default_field': default_field,
                'embedded_field': embedded_field,
                'embedded': False
            })

    def property2field(self, prop, instance=True, **kwargs):
        field_class = self._get_field_class_for_property(prop)
        if not instance:
            return field_class
        field_kwargs = self._get_field_kwargs_for_property(prop)
        field_kwargs.update(kwargs)
        ret = field_class(**field_kwargs)
        return ret

    def _get_field_kwargs_for_property(self, prop):
        kwargs = self.get_base_kwargs()
        if hasattr(prop, 'columns'):
            self._add_column_kwargs(kwargs, prop)
        if hasattr(prop, 'direction'):  # Relationship property
            self._add_relationship_kwargs(kwargs, prop)
        if getattr(prop, 'doc', None):  # Useful for documentation generation
            kwargs['description'] = prop.doc
        return kwargs

    def fields_for_model(self, model, include_fk=False, fields=None,
                         exclude=None):
        result = super(ModelResourceConverter, self).fields_for_model(
                model, include_fk, fields, exclude)
        result["self"] = APIUrl()
        return result


class CamelModelResourceConverter(ModelResourceConverter):
    """Convert a model to a schema that uses camelCase field names."""

    def _add_column_kwargs(self, kwargs, prop):
        """Add keyword arguments to kwargs (in-place) based on the passed in
        `Property`.
        """
        # TODO - Embedded field kwargs...
        super(CamelModelResourceConverter, self)._add_column_kwargs(
                kwargs, prop)
        kwargs["load_from"] = camelize(prop.key, uppercase_first_letter=False)
        kwargs["dump_to"] = camelize(prop.key, uppercase_first_letter=False)