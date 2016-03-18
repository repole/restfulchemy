"""
    restfulchemy.fields
    ~~~~~~~~~~~~~~~~~~~

    Marshmallow fields used in model resource schemas.

    :copyright: (c) 2016 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
import copy
from marshmallow.compat import basestring
from marshmallow.fields import Field, Nested, missing_
from marshmallow.utils import is_collection, get_value
from marshmallow.validate import ValidationError
from marshmallow_sqlalchemy.fields import Related, ensure_list
from restfulchemy import resource_class_registry
from sqlalchemy.inspection import inspect


class EmbeddedField(Field):

    """Contains a default field and an embeddable field.

    Member or method access will use the default field provided if the
    current state isn't embedded, or the embedded field provided if the
    current state is embedded.

    A common use case is to have a default field be a
    :class:`RelationshipUrl`, and the embedded field be a
    :class:`NestedRelated` field.

    """

    def __init__(self, default_field, embedded_field, embedded=False, *args,
                 **kwargs):
        """Construct an embeddable field.

        :param default_field: Default field to use when not embedded.
        :type default_field: :class:`~marshmallow.fields.Field`
        :param embedded_field: Field to use when embedded.
        :type embedded_field: :class:`~marshmallow.fields.Field`

        """
        self._embedded = embedded
        self._default_field = default_field
        self._embedded_field = embedded_field
        super(EmbeddedField, self).__init__(*args, **kwargs)

    def _rebind_field(self):
        """After embedding or unembedding, bind the new active field."""
        inactive_field = self.embedded_field
        if inactive_field == self.active_field:
            inactive_field = self.default_field
        schema = inactive_field.parent
        if schema is not None:
            if schema.load_only:
                self.active_field.load_only = True
            if schema.dump_only:
                self.active_field.dump_only = True
            schema.on_bind_field(inactive_field.name, self.active_field)
            self._add_to_schema(inactive_field.name, schema)

    def embed(self):
        """Embed the non default field."""
        if not self.embedded:
            self._embedded = True
            self._rebind_field()

    def unembed(self):
        """Restore the default field."""
        if self.embedded:
            self._embedded = False
            self._rebind_field()

    @property
    def embedded(self):
        """Return ``True`` if the embedded field is currently active."""
        return self._embedded

    @property
    def embedded_field(self):
        """Get the embedded field, regardless of if it is embedded."""
        return self._embedded_field

    @embedded_field.setter
    def embedded_field(self, value):
        """Replace the embedded field.

        :param value: A new field to use for when the current state is
            embedded.
        :type value: :class:`~marshmallow.fields.Field`

        """
        self._embedded_field = value

    @property
    def default_field(self):
        """Return the default, non embedded field."""
        return self._default_field

    @default_field.setter
    def default_field(self, value):
        """Replace the default field.

        :param value: A new field to use for when the current state is
            not embedded.
        :type value: :class:`~marshmallow.fields.Field`

        """
        self._default_field = value

    @property
    def active_field(self):
        """Return the embedded field if embedded, else the default."""
        if self.embedded:
            return self._embedded_field
        else:
            return self._default_field

    @property
    def name(self):
        """Get the ``active_field.name`` property."""
        return self.active_field.name

    @name.setter
    def name(self, value):
        """Set the ``active_field.name`` property.

        :param str value: The new ``name`` value to use for the field.

        """
        setattr(self.active_field, "name", value)

    @property
    def default(self):
        """Get the ``active_field.default`` property."""
        return self.active_field.default

    @default.setter
    def default(self, value):
        """Set the ``active_field.default`` property.

        :param str value: The new ``default`` value to use for the
            field.

        """
        setattr(self.active_field, "default", value)

    @property
    def attribute(self):
        """Get the ``active_field.attribute`` property."""
        return self.active_field.attribute

    @attribute.setter
    def attribute(self, value):
        """Set the ``active_field.attribute`` property.

        :param str value: The new ``attribute`` value to use for the
            field.

        """
        setattr(self.active_field, "attribute", value)

    @property
    def load_from(self):
        """Get the ``active_field.load_from`` property."""
        return self.active_field.load_from

    @load_from.setter
    def load_from(self, value):
        """Set the ``active_field.load_from`` property.

        :param str value: The new ``load_from`` value to use for the
            field.

        """
        setattr(self.active_field, "load_from", value)

    @property
    def dump_to(self):
        """Get the ``active_field.dump_to`` property."""
        return self.active_field.dump_to

    @dump_to.setter
    def dump_to(self, value):
        """Set the ``active_field.dump_to`` property.

        :param str value: The new ``dump_to`` value to use for the
            field.

        """
        setattr(self.active_field, "dump_to", value)

    @property
    def validate(self):
        """Get the ``active_field.validate`` property."""
        return self.active_field.validate

    @validate.setter
    def validate(self, value):
        """Set the ``active_field.validate`` property.

        :param str value: The new ``validate`` value to use for the
            field.

        """
        setattr(self.active_field, "validate", value)

    @property
    def validators(self):
        """Get the ``active_field.validators`` property."""
        return self.active_field.validators

    @validators.setter
    def validators(self, value):
        """Set the ``active_field.validators`` property.

        :param str value: The new ``validators`` value to use for the
            field.

        """
        setattr(self.active_field, "validators", value)

    @property
    def required(self):
        """Get the ``active_field.required`` property."""
        return self.active_field.required

    @required.setter
    def required(self, value):
        """Set the ``active_field.required`` property.

        :param str value: The new ``required`` value to use for the
            field.

        """
        setattr(self.active_field, "required", value)

    @property
    def allow_none(self):
        """Get the ``active_field.allow_none`` property."""
        return self.active_field.allow_none

    @allow_none.setter
    def allow_none(self, value):
        """Set the ``active_field.allow_none`` property.

        :param bool value: The new ``allow_none`` value to use for the
            field.

        """
        setattr(self.active_field, "allow_none", value)

    @property
    def load_only(self):
        """Get the ``active_field.load_only`` property."""
        return self.active_field.load_only

    @load_only.setter
    def load_only(self, value):
        """Set the ``active_field.load_only`` property.

        :param bool value: The new ``load_only`` value to use for the
            field.

        """
        setattr(self.active_field, "load_only", value)

    @property
    def dump_only(self):
        """Get the ``active_field.dump_only`` property."""
        return self.active_field.dump_only

    @dump_only.setter
    def dump_only(self, value):
        """Set the ``active_field.dump_only`` property.

        :param bool value: The new ``dump_only`` value to use for the
            field.

        """
        setattr(self.active_field, "dump_only", value)

    @property
    def missing(self):
        """Get the ``active_field.missing`` property."""
        return self.active_field.missing

    @missing.setter
    def missing(self, value):
        """Set the ``active_field.missing`` property.

        :param value: The new ``missing`` value to use for the field.

        """
        setattr(self.active_field, "missing", value)

    @property
    def metadata(self):
        """Get the ``active_field.metadata`` property."""
        return self.active_field.metadata

    @metadata.setter
    def metadata(self, value):
        """Set the ``active_field.metadata`` property.

        :param dict value: The new ``metadata`` value to use for the
            field.

        """
        setattr(self.active_field, "metadata", value)

    @property
    def parent(self):
        """Get the ``active_field.parent`` property."""
        return self.active_field.parent

    @parent.setter
    def parent(self, value):
        """Set the ``active_field.parent`` property.

        :param value: The new ``parent`` value to use for the field.

        """
        setattr(self.active_field, "parent", value)

    @property
    def error_messages(self):
        """Get the ``active_field.error_messages`` property."""
        return self.active_field.error_messages

    @error_messages.setter
    def error_messages(self, value):
        """Set the ``active_field.error_messages`` property.

        :param dict value: The new ``error_messages`` value to use for
            the field.

        """
        setattr(self.active_field, "error_messages", value)

    def get_value(self, attr, obj, accessor=None, default=missing_):
        """Call ``active_field.get_value``.

        :param str attr: Name of the attribute containing the desired
            value.
        :param obj: A generic object that contains the desired value.
        :param accessor: Function used to pull values from ``obj``.
            Defaults to :func:`~marshmallow.utils.get_value`.
        :type accessor: callable or None
        :param default: The default value to return if the attr can not
            be accessed in the obj.
        :return: The value of the object's attr.

        """
        return self.active_field.get_value(attr, obj, accessor, default)

    def _validate(self, value):
        """Call ``active_field._validate``.

        :param value: Value to be validated for this field.
        :raise ValidationError: If validation does not succeed.

        """
        return self.active_field._validate(value)

    def fail(self, key, **kwargs):
        """Call ``active_field.fail``.

        :param str key: The type of failure, used to choose which error
            message to include in the raised exception.
        :param kwargs: Key word args used for string replacement fields
            in the error message.
        :raise ValidationError: In all cases, raises an exception.

        """
        return self.active_field.fail(key, **kwargs)

    def _validate_missing(self, value):
        """Call ``active_field._validate_missing``.

        :param value: The value provided for this field.
        :raise ValidationError: If ``value`` is considered missing.

        """
        return self.active_field._validate_missing(value)

    def serialize(self, attr, obj, accessor=None):
        """Call ``active_field.serialize``.

        :param str attr: The attribute or key to get from the object.
        :param str obj: The object to pull the key from.
        :param accessor: Function used to pull values from ``obj``.
            Defaults to :func:`~marshmallow.utils.get_value`.
        :type accessor: callable or None
        :raise ValidationError: In case of formatting problem.
        :return: The serialized value.

        """
        return self.active_field.serialize(attr, obj, accessor)

    def deserialize(self, value, attr=None, data=None):
        """Call ``active_field.deserialize``.

        :param value: The value to be deserialized.
        :param str attr: The attribute/key in ``data`` to be
            deserialized.
        :param dict data: The raw input data passed to ``Schema.load``.
        :raise ValidationError: If an invalid value is passed or if a
            required value is missing.
        :return: The deserialized value.

        """
        return self.active_field.deserialize(value, attr, data)

    def _add_to_schema(self, field_name, schema):
        """Call ``active_field._add_to_schema``.

        :param str field_name: Field name set in schema.
        :param schema: This field's parent schema.
        :type schema: :class:`~marshmallow.schema.Schema`

        """
        return self.active_field._add_to_schema(field_name, schema)

    def _serialize(self, value, attr, obj):
        """Call ``active_field._serialize``.

        :param str attr: The attribute or key to get from the object.
        :param str obj: The object to pull the key from.
        :raise ValidationError: In case of formatting problem.
        :return: The serialized value.

        """
        return self.active_field._serialize(value, attr, obj)

    def _deserialize(self, value, attr, data):
        """Call ``active_field._deserialize``.

        :param value: The value to be deserialized.
        :param str attr: The attribute/key in ``data`` to be
            deserialized.
        :param dict data: The raw input data passed to ``Schema.load``.
        :raise ValidationError: If an invalid value is passed or if a
            required value is missing.
        :return: The deserialized value.

        """
        return self.active_field._deserialize(value, attr, data)

    @property
    def context(self):
        """Use the active_field implementation of context."""
        return self.active_field.context

    @property
    def root(self):
        """Use the active_field implementation of root."""
        return self.active_field.root

    def __deepcopy__(self, memo):
        """Takes care of deepcopying the embedded and default fields.

        :param dict memo: Standard deepcopy memo dict containing id to
            object mapping.

        """
        ret = super(EmbeddedField, self).__deepcopy__(memo)
        ret._default_field = copy.deepcopy(self._default_field)
        ret._embedded_field = copy.deepcopy(self._embedded_field)
        return ret


class NestedRelated(Nested, Related):

    """A nested relationship field for use in a `ModelSchema`."""

    def __init__(self, nested, default=missing_, exclude=tuple(), only=None,
                 many=False, column=None, **kwargs):
        """Initialize a nested related field.

        :param nested: The Schema class or class name (string) to nest,
            or ``"self"`` to nest a :class:`~marshmallow.schema.Schema`
            within itself.
        :param default: Default value to use if attribute is missing.
        :param exclude: Fields to exclude.
        :type exclude: list, tuple, or None
        :param only: A tuple or string of the field(s) to marshal. If
            `None`, all fields will be marshalled. If a field name
            (string) is given, only a single value will be returned as
            output instead of a dictionary. This parameter takes
            precedence over ``exclude``.
        :type only: tuple, str, or None
        :param bool many: Whether the field is a collection of objects.
        :param kwargs: The same keyword arguments that
            :class:`~marshmallow.fields.Field` receives.

        """
        super(NestedRelated, self).__init__(
            nested=nested,
            default=default,
            exclude=exclude,
            only=only,
            many=many,
            **kwargs)
        self.columns = ensure_list(column or [])

    @property
    def model(self):
        """The model associated with this relationship."""
        schema = self.parent
        return schema.opts.model

    @property
    def related_keys(self):
        """Gets a list of id keys associated with this nested obj.

        Note the hierarchy of id keys to return:

        1. If the attached schema for this nested field has an id_keys
           attr, use those keys.
        2. Else, if this field had a columns arg passed when
           initialized, use those column names.
        3. Else, use the primary key columns.

        """
        # schema here is for this nested field, not the parent.
        if hasattr(self.schema, "id_keys"):
            columns = [
                self.related_model.__mapper__.columns[key_name]
                for key_name in self.schema.id_keys
            ]
            return [
                self.related_model.__mapper__.get_property_by_column(column)
                for column in columns
            ]
        else:
            return super(NestedRelated, self).related_keys

    @property
    def schema(self):
        """The schema corresponding to this relationship."""
        result = super(NestedRelated, self).schema
        if hasattr(result, "gettext"):
            result.gettext = self.parent.gettext
        result.root = self
        result.parent = self
        return result

    def _deserialize(self, value, *args, **kwargs):
        """Deserialize data into a SQLAlchemy relationship field.

        In the case of a relationship with many items, the behavior of
        this field varies in a few key ways depending on whether the
        parent form has `partial` set to `True` or `False`.
        If `True`, items can be explicitly added or removed from a
        relationship, but the rest of the relationship will remain
        intact.
        If `False`, the relationship will be set to an empty list, and
        only items included in the supplied data will in the
        relationship.
        Important to note also that updates to items contained in this
        relationship will be done so using ``partial=True``, regardless
        or what the value of the parent schema's ``partial`` attribute
        is. The only exception to this is in the creation of a new item
        to be placed in the relationship, in which case
        ``partial=False`` is always used.

        :param value: Data for this field.
        :type value: list of dictionaries or dict
        :return: The deserialized form of this relationship. In the
            case of a relationship that doesn't use a list, this is
            a single SQLAlchemy object (or `None`). Otherwise a list
            of SQLAlchemy objects is returned.

        """
        strict = self.parent.strict
        result = None
        parent = self.parent.instance
        if self.many:
            data = value
            if not is_collection(value):
                self.fail('type', input=value, type=value.__class__.__name__)
            else:
                if not self.parent.partial:
                    setattr(parent, self.name, [])
        else:
            # Treat this like a list relation until it comes time
            # to actually modify the relationship.
            data = [value]
        errors = {}
        # each item in value is a sub instance
        for i, obj in enumerate(data):
            # check if there's an explicit operation included
            if hasattr(obj, "pop"):
                operation = obj.pop("$op", None)
            else:
                operation = None
            # check wheather this data has value(s) for
            # the indentifier columns.
            has_identifier = True
            for column in self.related_keys:
                if column.key not in obj:
                    has_identifier = False
            if has_identifier:
                with self.session.no_autoflush:
                    # If the parent object hasn't yet been persisted,
                    # autoflush can cause an error since it is yet
                    # to be fully formed.
                    instance = self.session.query(
                        self.related_model).filter_by(**{
                            column.key: obj.get(column.key)
                            for column in self.related_keys
                        }).first()
            else:
                instance = None
            instance_is_in_relation = False
            if instance is None:
                # New object, try to create it.
                instance, sub_errors = self.schema.load(
                    obj,
                    session=self.session,
                    instance=self.related_model(),
                    partial=False,
                    many=False)
                if sub_errors:
                    if self.many:
                        errors[i] = sub_errors
                    else:
                        errors = sub_errors
                    if strict:
                        raise ValidationError(errors, data=value)
                    else:
                        continue
            else:
                # Try loading this data using the nested schema
                loaded_instance, sub_errors = self.schema.load(
                    obj,
                    session=self.session,
                    instance=instance,
                    partial=True,
                    many=False)
                with_parentable = False
                if self.parent.instance is not None:
                    if inspect(self.parent.instance).persistent:
                        with_parentable = True
                if not sub_errors and loaded_instance == instance:
                    # Instance with this primary key exists
                    # Data provided validates
                    # Now check to see if this instance is already
                    # in the parent relationship.
                    if with_parentable:
                        in_relation_instance = self.session.query(
                            self.related_model).with_parent(
                                self.parent.instance).filter_by(**{
                                    column.key: obj.get(column.key)
                                    for column in self.related_keys
                                }).first()
                        if in_relation_instance == instance:
                            instance_is_in_relation = True
                    else:
                        if isinstance(getattr(parent, self.name), list):
                            if instance in getattr(parent, self.name):
                                instance_is_in_relation = True
                        elif getattr(parent, self.name) == instance:
                            instance_is_in_relation = True
                else:
                    # error
                    # TODO - decide how to do nested errors
                    if self.many:
                        errors[i] = sub_errors
                    else:
                        errors = sub_errors
                    if strict:
                        raise ValidationError(errors, data=value)
                    else:
                        continue
            if not sub_errors and instance is not None and self.many:
                if operation == "remove":
                    if instance_is_in_relation:
                        if self.parent.partial:
                            # no need to remove if not partial, as the
                            # list will already be empty.
                            relation = getattr(parent, self.name)
                            relation.remove(instance)
                    # TODO - elif strict: error
                elif operation is None or operation == "add":
                    if not instance_is_in_relation:
                        relation = getattr(parent, self.name)
                        relation.append(instance)
                # TODO - elif strict: error
                result = getattr(parent, self.name)
            elif not sub_errors and not self.many:
                setattr(parent, self.name, instance)
                result = instance
        if errors:
            raise ValidationError(errors, data=value)
        return result


class RelationshipUrl(Field):

    """Text field, displays the sub resource url of a relationship."""

    def __init__(self, default=missing_, attribute=None, load_from=None,
                 dump_to=None, error=None, validate=None, required=False,
                 allow_none=None, load_only=False, dump_only=False,
                 missing=missing_, error_messages=None, resource=None,
                 **metadata):
        """Initialize a relationship url field.

        :param default: If set, this value will be used during
            serialization if the input value is missing. If not set, the
            field will be excluded from the serialized output if the
            input value is missing. May be a value or a callable.
        :param str attribute: The name of the attribute to get the value
            from. If `None`, assumes the attribute has the same name as
            the field.
        :type attribute: str or None
        :param load_from: Additional key to look for when deserializing.
            Will only be checked if the field's name is not found on the
            input dictionary. If checked, it will return this parameter
            on error.
        :type load_from: str or None
        :param dump_to: Field name to use as a key when serializing.
        :type dump_to: str or None
        :param validate: Validator or collection of validators that are
            called during deserialization. Validator takes a field's
            input value as its only parameter and returns a boolean.
            If it returns `False`, an :exc:`ValidationError` is raised.
        :type validate: callable or None
        :param bool required: Raise a
            :exc:`~marshmallow.exceptions.ValidationError` if the field
            value is not supplied during deserialization.
        :param bool allow_none: Set this to `True` if `None` should be
            considered a valid value during validation/deserialization.
            If ``missing=None`` and ``allow_none`` is unset, will
            default to `True`. Otherwise, the default is `False`.
        :param bool load_only: If `True` skip this field during
            serialization, otherwise its value will be present in the
            serialized data.
        :param bool dump_only: If `True` skip this field during
            deserialization, otherwise its value will be present in the
            deserialized object. In the context of an HTTP API, this
            effectively marks the field as "read-only".
        :param missing: Default deserialization value for the field if
            the field is not found in the input data. May be a value
            or a callable.
        :param error_messages: Overrides for field error messages.
        :type error_messages: dict or None
        :param metadata: Extra arguments to be stored as metadata.

        """
        self._resource_arg = resource
        super(RelationshipUrl, self).__init__(
            default=default,
            attribute=attribute,
            load_from=load_from,
            dump_to=dump_to,
            error=error,
            validate=validate,
            required=required,
            allow_none=allow_none,
            load_only=load_only,
            dump_only=dump_only,
            missing=missing,
            error_messages=error_messages,
            **metadata)

    @property
    def resource_class(self):
        """Get the nested resource class."""
        # Ensure that only parameter is a tuple
        if isinstance(self._resource_arg, basestring):
            return resource_class_registry.get_class(self._resource_arg)
        else:
            return self._resource_arg

    def serialize(self, attr, obj, accessor=None):
        """Serialize a relationship sub-resource url.

        :param str attr: The attribute name of this field. Unused.
        :param str obj: The object to pull any needed info from.
        :param accessor: Function used to pull values from ``obj``.
            Unused.
        :type accessor: callable or None
        :return: The serialized relationship url value.
        :rtype: str

        """
        url = ""
        if self.parent and "self" in self.parent.fields:
            url += self.parent.fields["self"].serialize("self", obj)
        relationship_name = self.dump_to or self.name
        url += "/" + relationship_name
        return url


class APIUrl(Field):

    """Text field, displays the url of the resource it's attached to."""

    def serialize(self, attr, obj, accessor=None):
        """Serialize an API url.

        :param str attr: The attribute name of this field. Unused.
        :param str obj: The object to pull any needed info from.
        :param accessor: Function used to pull values from ``obj``.
            Defaults to :func:`~marshmallow.utils.get_value`.
        :type accessor: callable or None
        :raise ValidationError: In case of formatting problem.
        :return: The serialized API url value.

        """
        # TODO - Better safety checking
        accessor_func = accessor or get_value
        id_keys = self.parent.id_keys
        result = "/" + self.parent.api_endpoint_base
        for column in id_keys:
            if hasattr(obj, column):
                val = accessor_func(column, obj, missing_)
                result += "/" + str(val)
        return result
