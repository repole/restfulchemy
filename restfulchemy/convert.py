"""
    restfulchemy.converter
    ~~~~~~~~~~~~~~~~~~~~~~

    Convert SQLAlchemy models into Marshmallow schemas.

    :copyright: (c) 2016 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from inflection import camelize
from marshmallow_sqlalchemy.convert import ModelConverter
from restfulchemy.fields import (EmbeddedField, NestedRelated, RelationshipUrl,
                                 APIUrl)


class ModelResourceConverter(ModelConverter):

    """Convert a model's fields for use in a `ModelResourceSchema`."""

    def _get_field_class_for_property(self, prop):
        """Determine what class to use for a field based on ``prop``.

        :param prop: A column property belonging to a sqlalchemy model.
        :type prop: :class:`~sqlalchemy.orm.properties.ColumnProperty`
        :return: A field class corresponding to the provided ``prop``.
        :rtype: type

        """
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
        """Update the provided kwargs based on the prop given.

        :param dict kwargs: A dictionary of kwargs to pass to the
            eventual field constructor. This argument is modified
            in place.
        :param prop: A column property used to determine how
            ``kwargs`` should be updated.
        :type prop: :class:`~sqlalchemy.orm.properties.ColumnProperty`

        """
        super(ModelResourceConverter, self)._add_column_kwargs(
            kwargs, prop.columns[0])

    def _add_relationship_kwargs(self, kwargs, prop):
        """Update the provided kwargs based on the relationship given.

        :param dict kwargs: A dictionary of kwargs to pass to the
            eventual field constructor. This argument is modified
            in place.
        :param prop: A relationship property used to determine how
            ``kwargs`` should be updated.
        :type prop:
            :class:`~sqlalchemy.orm.properties.RelationshipProperty`

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

    def property2field(self, prop, instance=True, **kwargs):
        """

        :param prop: A column or relationship property used to
            determine a corresponding field.
        :type prop: :class:`~sqlalchemy.orm.properties.ColumnProperty`
            or :class:`~sqlalchemy.orm.properties.RelationshipProperty`
        :param instance: `True` if this method should return an actual
            instance of a field, `False` to return the actual field
            class.
        :param kwargs: Keyword args to be used in the construction of
            the field.
        :return: Depending on the value of ``instance``, either a field
            or a field class.
        :rtype: :class:`~marshmallow.fields.Field` or type

        """
        field_class = self._get_field_class_for_property(prop)
        if not instance:
            return field_class
        field_kwargs = self._get_field_kwargs_for_property(prop)
        field_kwargs.update(kwargs)
        ret = field_class(**field_kwargs)
        return ret

    def _get_field_kwargs_for_property(self, prop):
        """Get a dict of kwargs to use for field construction.

        :param prop: A column or relationship property used to
            determine what kwargs should be passed to the
            eventual field constructor.
        :type prop: :class:`~sqlalchemy.orm.properties.ColumnProperty`
            or :class:`~sqlalchemy.orm.properties.RelationshipProperty`
        :return: A dict of kwargs to pass to the eventual field
            constructor.
        :rtype: dict

        """
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
        """Generate fields for the provided model.

        :param model: The SQLAlchemy model the generated fields
            correspond to.
        :param bool include_fk: `True` if fields should be generated for
            foreign keys, `False` otherwise.
        :param fields: A collection of field names to generate.
        :type fields: :class:`~collections.Iterable` or None
        :param exclude: A collection of field names not to generate.
        :type exclude: :class:`~collections.Iterable` or None
        :return: Generated fields corresponding to each model property.
        :rtype: list

        """
        result = super(ModelResourceConverter, self).fields_for_model(
            model, include_fk, fields, exclude)
        result["self"] = APIUrl()
        return result


class CamelModelResourceConverter(ModelResourceConverter):

    """Convert a model to a schema that uses camelCase field names."""

    def _add_column_kwargs(self, kwargs, prop):
        """Update the provided kwargs based on the prop given.

        :param dict kwargs: A dictionary of kwargs to pass to the
            eventual field constructor. This argument is modified
            in place.
        :param prop: A column property used to determine how
            ``kwargs`` should be updated.
        :type prop: :class:`~sqlalchemy.orm.properties.ColumnProperty`

        """
        super(CamelModelResourceConverter, self)._add_column_kwargs(
            kwargs, prop)
        kwargs["load_from"] = camelize(prop.key, uppercase_first_letter=False)
        kwargs["dump_to"] = camelize(prop.key, uppercase_first_letter=False)
