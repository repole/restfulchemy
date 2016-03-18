"""
    restfulchemy.resource
    ~~~~~~~~~~~~~~~~~~~~~

    Base classes for building resources and model resources.

    :copyright: (c) 2016 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from marshmallow.compat import with_metaclass
from mqlalchemy import apply_mql_filters, InvalidMQLException
from mqlalchemy.utils import dummy_gettext
from restfulchemy import resource_class_registry
from restfulchemy.fields import EmbeddedField, NestedRelated
from restfulchemy.query_builder import (
    apply_load_options, apply_sorts, apply_offset_and_limit, SortInfo)
from sqlalchemy.exc import SQLAlchemyError


class UnprocessableEntityError(Exception):

    """Exception for when provided data is unable to be deserialized."""

    pass


class BadRequestException(Exception):

    """Exception for when a request is unable to be processed."""

    pass


class ResourceNotFoundError(Exception):

    """Exception for when a requested resource cannot be found."""

    pass


class ResourceABC(object):

    """Abstract resource base class."""

    def get(self, ident):
        """Get an instance of this resource.

        :param ident: Identifying info for the resource.
        :return: The resource itself if found.
        :raise ResourceNotFoundError: If no such resource exists.

        """
        raise NotImplementedError

    def post(self, data):
        """Create a resource with the supplied data.

        :param data: Data used to create the resource.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: The created resource.

        """
        raise NotImplementedError

    def put(self, ident, data):
        """Replace the identified resource with the supplied one.

        :param ident: Identifying info for the resource.
        :param data: Data used to replace the resource.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: The replaced resource.

        """
        raise NotImplementedError

    def patch(self, ident, data):
        """Update the identified resource with the supplied data.

        :param ident: Identifying info for the resource.
        :param data: Data used to update the resource.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: The updated resource.

        """
        raise NotImplementedError

    def delete(self, ident):
        """Delete the identified resource.

        :param ident: Identifying info for the resource.
        :raise ResourceNotFoundError: If no such resource exists.
        :return: `None`

        """
        raise NotImplementedError

    def get_collection(self):
        """Get a collection of resources."""
        raise NotImplementedError

    def post_collection(self, data):
        """Create multiple resources in the collection of resources.

        :param data: Data used to create the collection of resources.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: `None`

        """
        raise NotImplementedError

    def put_collection(self, data):
        """Replace the entire collection of resources.

        :param data: Data used to replace the collection of resources.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: `None`

        """
        raise NotImplementedError

    def patch_collection(self, data):
        """Update the collection of resources.

        :param data: Data used to update the collection of resources.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: `None`

        """
        raise NotImplementedError

    def delete_collection(self):
        """Delete all members of the collection of resources."""
        raise NotImplementedError


class ModelResourceOpts(object):

    """Meta class options for use with a `ModelResource`.

    A ``schema_class`` option must be provided.

    Example usage:

    .. code-block:: python

        class UserResource(ModelResource):
            class Meta:
                schema_class = UserSchema

    """

    def __init__(self, meta):
        """Handle the meta class attached to a `ModelResource`.

        :param meta: The meta class attached to a
            :class:`~restfulchemy.resource.ModelResource`.

        """
        self.schema_class = getattr(meta, "schema_class", None)


class ModelResourceMeta(type):

    """Meta class inherited by `ModelResource`.

    This is ultimately responsible for attaching an ``opts`` object to
    :class:`ModelResource`, as well as registering that class with the
    ``resource_class_registry``.

    """

    def __new__(mcs, name, bases, attrs):
        """Sets up meta class options for a given ModelResource class.

        :param mcs: This :class:`ModelResourceMeta` class.
        :param str name: Class name of the
            :class:`~restfulchemy.resource.ModelResource` that this meta
            class is attached to.
        :param tuple bases: Base classes the associated class inherits
            from.
        :param dict attrs: Dictionary of info pertaining to the class
            this meta class is attached to. Includes the __module__ the
            class is in, the __qualname__ of the class, and potentially
            __doc__ for the class.

        """
        klass = super(ModelResourceMeta, mcs).__new__(mcs, name, bases, attrs)
        meta = getattr(klass, 'Meta')
        klass.opts = klass.OPTIONS_CLASS(meta)
        return klass

    def __init__(cls, name, bases, attrs):
        """Initializes the meta class for a `ModelResource` class.

        :param cls: This :class:`ModelResourceMeta` class.
        :param name: Class name of the
            :class:`~restfulchemy.resource.ModelResource` that this meta
            class is attached to.
        :param tuple bases: Base classes the associated class inherits
            from.
        :param dict attrs: Dictionary of info pertaining to the class
            this meta class is attached to. Includes the __module__ the
            class is in, the __qualname__ of the class, and potentially
            __doc__ for the class.

        """
        super(ModelResourceMeta, cls).__init__(name, bases, attrs)
        resource_class_registry.register(name, cls)


class BaseModelResource(ResourceABC):

    """Model API Resources should inherit from this object."""

    OPTIONS_CLASS = ModelResourceOpts

    class Meta(object):
        """Options object for a Resource.

        Example usage: ::

            class Meta:
                schema_class = MyModelSchema

        Available options:

        - ``schema_class``: The model schema this resource is built around.

        """
        pass

    def __init__(self, session, schema_context=None, page_max_size=None,
                 gettext=None):
        """Creates a new instance of the model.

        :param session: Database session to use for any resource
            actions.
        :type session: :class:`~sqlalchemy.orm.session.Session`
        :param schema_context: Context used to alter the schema used
            for this resource. For example, may contain the current
            authorization status of the current request.
        :type schema_context: dict or None
        :param page_max_size: Used to determine the maximum number of
            results to return by :meth:`get_collection`.
        :type page_max_size: int, callable, or None
        :param gettext: Used to translate any error messages that may
            pop up.
        :type gettext: int, callable, or None

        """
        self._page_max_size = page_max_size
        self._schema_context = schema_context
        self._session = session
        self.gettext = gettext
        if self.gettext is None:
            self.gettext = dummy_gettext

    @property
    def model(self):
        """Get the model class associated with this resource."""
        return self.schema_class.opts.model

    @property
    def schema_class(self):
        """Get the schema class associated with this resource."""
        return self.opts.schema_class

    def whitelist(self, key):
        """Determine whether a field is valid to be queried.

        Uses the load_only property for the resource's schema fields
        to determine whether the field should be queryable. Also handles
        nested queries without issue.

        :param str key: Dot notation field name. For example, if trying
            to query an album, this may look something like
            ``"tracks.playlists.track_id"``.

        """
        split_keys = key.split(".")
        schema = self.schema_class(
            context=self.schema_context,
            gettext=self.gettext)
        for i, key in enumerate(split_keys):
            if key in schema.fields:
                field = schema.fields[key]
                if field.load_only:
                    return False
                elif isinstance(field, EmbeddedField):
                    schema.embed([key])
                    if hasattr(field.active_field, "schema"):
                        schema = field.active_field.schema
                    else:
                        return False
                elif isinstance(field, NestedRelated):
                    schema = field.schema
                else:
                    if i != (len(split_keys) - 1):
                        return False
            else:
                return False
        return True

    def convert_key_name(self, key):
        """Given a dumped key name, convert to the name of the field.

        :param str key: Name of the field as it was serialized, using
            dot notation for nested fields.

        """
        schema = self.schema_class(
            context=self.schema_context,
            gettext=self.gettext)
        split_keys = key.split(".")
        result_keys = []
        for key in split_keys:
            field = None
            if hasattr(schema, "fields_by_dump_to"):
                if key in schema.fields_by_dump_to:
                    field = schema.fields_by_dump_to[key]
            else:
                for field_name in schema.fields:
                    if schema.fields[field_name].dump_to == key:
                        field = schema.fields[field_name]
                        break
            if field is not None:
                result_keys.append(field.name)
                if isinstance(field, EmbeddedField):
                    schema.embed([key])
                    if hasattr(field.active_field, "schema"):
                        schema = field.active_field.schema
                if hasattr(field, "schema"):
                    schema = field.schema
            else:
                # Invalid key name, no matching field found.
                return None
        return ".".join(result_keys)

    @property
    def session(self):
        """Get a db session to use for this request."""
        if callable(self._session):
            return self._session()
        else:
            return self._session

    @property
    def page_max_size(self):
        """Get the max number of resources to return."""
        if callable(self._page_max_size):
            return self._page_max_size()
        else:
            return self._page_max_size

    @property
    def schema_context(self):
        """Return the schema context for this resource."""
        if callable(self._schema_context):
            return self._schema_context()
        else:
            return self._schema_context

    def _get_ident_filters(self, ident):
        """Generate MQLAlchemy filters using a resource identity.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.

        """
        filters = {}
        if not (isinstance(ident, tuple) or
                isinstance(ident, list)):
            ident = (ident,)
        schema = self.schema_class(
            context=self.schema_context,
            gettext=self.gettext)
        for i, field_name in enumerate(schema.id_keys):
            field = schema.fields.get(field_name)
            filter_name = field.dump_to or field_name
            filters[filter_name] = ident[i]
        return filters

    def _get_instance(self, ident):
        """Given an identity, get the associated SQLAlchemy instance.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.

        """
        filters = self._get_ident_filters(ident)
        query = self.session.query(self.model)
        query = apply_mql_filters(
            query,
            model_class=self.model,
            filters=filters,
            whitelist=self.whitelist,
            stack_size_limit=100,
            convert_key_names_func=self.convert_key_name,
            gettext=self.gettext)
        return query.first()

    def _get_schema_and_query(self, session, filters, fields=None,
                              embeds=None, strict=True):
        """Used to generate a schema and query for this request.

        :param session: See :meth:`get` for more info.
        :type session: :class:`~sqlalchemy.orm.session.Session` or
            :class:`~sqlalchemy.orm.query.Query`
        :param filters: MQLAlchemy filters to be applied on this query.
        :type filters: list or None
        :param fields: Names of fields to be included in the result.
        :type fields: list or None
        :param embeds: A list of relationship and relationship field
            names to be included in the result.
        :type embeds: list or None
        :param bool strict: If `True`, will raise an exception when bad
            parameters are passed. If `False`, will quietly ignore any
            bad input and treat it as if none was provided.
        :raise BadRequestException: Invalid filters, fields, or embeds
            will result in a raised exception if strict is `True`.
        :return: A schema and query conforming to the supplied
            parameters.
        :rtype: :class:`~restfulchemy.schema.ModelResourceSchema`,
            :class:`~sqlalchemy.orm.query.Query`

        """
        _ = self.gettext
        if hasattr(session, "query"):
            query = session.query(self.model)
        else:
            query = session
        # embed converting
        # name mapping used purely for error purposes
        # key is converted name, value is orig attr name
        embed_name_mapping = {}
        converted_embeds = []
        embed_fields = set()
        if isinstance(embeds, list):
            for embed in embeds:
                converted_embed = self.convert_key_name(embed)
                embed_name_mapping[converted_embed] = embed
                if converted_embed is None:
                    if strict:
                        raise BadRequestException(
                            {"error": _("Invalid embed supplied: %(embed)s",
                                        embed=embed)})
                elif converted_embed:
                    # used so if a fields param is provied, embeds are
                    # still included.
                    embed_fields.add(converted_embed.split(".")[0])
                converted_embeds.append(converted_embed)
        elif embeds is not None and strict:
            raise BadRequestException(
                {"error": _("Invalid embeds supplied: %(embeds)s",
                            embeds=embeds)})
        # fields
        converted_fields = []
        if isinstance(fields, list):
            for field in fields:
                converted_field = self.convert_key_name(field)
                if converted_field is None:
                    if strict:
                        raise BadRequestException(
                            {"error": _("Invalid field supplied: %(field)s",
                                        field=field)})
                elif converted_field:
                    converted_fields.append(converted_field)
        elif fields is not None and strict:
            raise BadRequestException(
                {"error": _("Invalid fields supplied: %(fields)s",
                            fields=fields)})
        if converted_fields:
            for embed_field in embed_fields:
                if embed_field not in converted_fields:
                    converted_fields.append(embed_field)
            schema = self.schema_class(
                only=tuple(converted_fields),
                context=self.schema_context,
                gettext=self.gettext)
        else:
            schema = self.schema_class(
                context=self.schema_context,
                gettext=self.gettext)
        # actually attempt to embed now
        for converted_embed in converted_embeds:
            try:
                schema.embed([converted_embed])
                # load options for joined loads based on embeds
                query = apply_load_options(
                    query, self.model, [converted_embed])
            except AttributeError:
                if strict:
                    raise BadRequestException(
                        {"error": _("Invalid embed supplied: %(key)s",
                                    key=embed_name_mapping[converted_embed])})
        # apply filters
        try:
            query = apply_mql_filters(
                query,
                self.model,
                filters=filters,
                whitelist=self.whitelist,
                stack_size_limit=100,
                convert_key_names_func=self.convert_key_name,
                gettext=self.gettext)
        except InvalidMQLException as ex:
            if strict:
                raise BadRequestException({"error": str(ex)})
        return schema, query

    def get(self, ident, fields=None, embeds=None, session=None, strict=True):
        """Get the identified resource.

        :param ident: A value used to identify this resource. If the
            schema associated with this resource has multiple
            ``id_keys``, this value may be a list or tuple.
        :param fields: Names of fields to be included in the result.
        :type fields: list or None
        :param embeds: A list of relationship and relationship field
            names to be included in the result.
        :type embeds: list or None
        :param session: Optional sqlalchemy session override. May also
            be a partially formed SQLAlchemy query, allowing for
            sub-resource queries by using
            :meth:~`sqlalchemy.orm.query.Query.with_parent`.
        :type session: :class:`~sqlalchemy.orm.session.Session` or
            :class:`~sqlalchemy.orm.query.Query`
        :param bool strict: If `True`, will raise an exception when bad
            parameters are passed. If `False`, will quietly ignore any
            bad input and treat it as if none was provided.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise BadRequestException: Invalid fields or embeds will result
            in a raised exception if strict is set to `True`.
        :return: The resource itself if found.
        :rtype: dict

        """
        _ = self.gettext
        filters = {}
        if not (isinstance(ident, tuple) or
                isinstance(ident, list)):
            ident = (ident,)
        if session is None:
            session = self.session
        schema = self.schema_class(
            context=self.schema_context,
            gettext=self.gettext)
        for i, field_name in enumerate(schema.id_keys):
            field = schema.fields.get(field_name)
            filter_name = field.dump_to or field_name
            filters[filter_name] = ident[i]
        schema, query = self._get_schema_and_query(
            session=session,
            filters=filters,
            fields=fields,
            embeds=embeds,
            strict=strict)
        instance = query.first()
        if instance is not None:
            return schema.dump(instance).data
        else:
            raise ResourceNotFoundError(_("Resource not found."))

    def post(self, data):
        """Create a new resource and store it in the db.

        :param dict data: Data used to create a new resource.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: The created resource.
        :rtype: dict

        """
        schema = self.schema_class(
            partial=False,
            context=self.schema_context,
            gettext=self.gettext)
        instance, errors = schema.load(data, session=self.session)
        if errors:
            self.session.rollback()
            raise UnprocessableEntityError(errors)
        else:
            self.session.add(instance)
            try:
                self.session.commit()
            except SQLAlchemyError:
                self.session.rollback()
                raise UnprocessableEntityError()
            return schema.dump(instance).data

    def put(self, ident, data):
        """Replace the current object with the supplied one.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.
        :param dict data: Data used to replace the resource.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: The replaced resource.
        :rtype: dict

        """
        obj = data
        instance = self._get_instance(ident)
        schema = self.schema_class(
            partial=False,
            instance=instance,
            context=self.schema_context,
            gettext=self.gettext)
        instance, errors = schema.load(
            obj, session=self.session)
        if errors:
            self.session.rollback()
            raise UnprocessableEntityError(errors)
        if instance:
            try:
                self.session.commit()
            except SQLAlchemyError:
                self.session.rollback()
                raise UnprocessableEntityError()
            return schema.dump(instance).data

    def patch(self, ident, data):
        """Update the identified resource with the supplied data.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.
        :param dict data: Data used to update the resource.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: The updated resource.
        :rtype: dict

        """
        obj = data
        instance = self._get_instance(ident)
        schema = self.schema_class(
            partial=True,
            instance=instance,
            context=self.schema_context,
            gettext=self.gettext)
        instance, errors = schema.load(
            obj, session=self.session)
        if errors:
            self.session.rollback()
            raise UnprocessableEntityError(errors)
        if instance:
            try:
                self.session.commit()
            except SQLAlchemyError:
                self.session.rollback()
                raise UnprocessableEntityError()
            return schema.dump(instance).data

    def delete(self, ident):
        """Delete the identified resource.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.
        :raise ResourceNotFoundError: If no such resource exists.
        :return: `None`

        """
        _ = self.gettext
        instance = self._get_instance(ident)
        if instance:
            self.session.remove(instance)
            try:
                self.session.commit()
            except SQLAlchemyError:
                self.session.rollback()
                raise UnprocessableEntityError()
        else:
            raise ResourceNotFoundError(_("Resource not found."))

    def get_collection(self, filters=None, fields=None, embeds=None,
                       sorts=None, offset=None, limit=None, session=None,
                       strict=True):
        """Get a collection of resources.

        :param filters: MQLAlchemy filters to be applied on this query.
        :type filters: list or None
        :param fields: Names of fields to be included in the result.
        :type fields: list or None
        :param embeds: A list of relationship and relationship field
            names to be included in the result.
        :type embeds: list or None
        :param sorts: Sorts to be applied to this query.
        :type sorts: list of :class:`SortInfo`, or None
        :param offset: Standard SQL offset to be applied to the query.
        :type offset: int or None
        :param limit: Standard SQL limit to be applied to the query.
        :type limit: int or None
        :param session: Optional sqlalchemy session override. See
            :meth:`get` for more info.
        :type session: :class:`~sqlalchemy.orm.session.Session` or
            :class:`~sqlalchemy.orm.query.Query`
        :param bool strict: If `True`, will raise an exception when bad
            parameters are passed. If `False`, will quietly ignore any
            bad input and treat it as if none was provided.
        :raise BadRequestException: Invalid filters, sorts, fields,
            embeds, offset, or limit will result in a raised exception
            if strict is set to `True`.
        :return: Resources meeting the supplied criteria.
        :rtype: list

        """
        _ = self.gettext
        if filters is None:
            filters = {}
        if session is None:
            session = self.session
        schema, query = self._get_schema_and_query(
            session=session,
            filters=filters,
            fields=fields,
            embeds=embeds,
            strict=strict)
        # sort
        if sorts:
            if isinstance(sorts, list):
                for sort in sorts:
                    if not isinstance(sort, SortInfo):
                        if strict:
                            raise BadRequestException(
                                {"error": _(
                                    "The sort provided %(sort)s is invalid.",
                                    sort=sort)})
                        else:
                            continue
                    try:
                        query = apply_sorts(
                            query, [sort], self.convert_key_name)
                    except AttributeError:
                        if strict:
                            raise BadRequestException(
                                {"error": _(
                                    "The sort provided for field %(field)s "
                                    "is invalid.",
                                    field=sort.attr)})
            elif strict:
                raise BadRequestException(
                    {"error": _("The sorts provided must be a list.")})
        # offset/limit
        if limit is not None:
            try:
                limit = int(limit)
            except ValueError:
                if strict:
                    raise BadRequestException(
                        {"error": _(
                            "The limit provided (%(limit)s) can not be "
                            "converted to an integer.",
                            limit=limit)})
                else:
                    limit = self.page_max_size
        if (limit is not None and
                isinstance(self.page_max_size, int) and
                limit > self.page_max_size):
            if strict:
                raise BadRequestException(
                    {"error": _(
                        "The limit provided (%(limit)d) is greater than the "
                        "max page size allowed (%(max_page_size)d).",
                        limit=limit,
                        max_page_size=self.page_max_size)})
            else:
                limit = self.page_max_size
        if offset:
            try:
                offset = int(offset)
            except ValueError:
                if strict:
                    raise BadRequestException(
                        {"error": _(
                            "The offset provided (%(offset)s) can not be "
                            "converted to an integer.",
                            offset=offset)})
                else:
                    offset = 0
        try:
            query = apply_offset_and_limit(query, offset, limit)
        except ValueError:
            raise BadRequestException(
                {"error": _(
                    "The provided offset (%(offset)s) and limit (%(limit)s) "
                    "can not be applied to the query.",
                    offset=offset,
                    limit=limit)})
        records = query.all()
        # get result
        dump = schema.dump(records, many=True)
        return dump.data

    def post_collection(self, data):
        """Create multiple resources in the collection of resources.

        :param list data: List of resources to be created.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: `None`

        """
        _ = self.gettext
        if not isinstance(data, list):
            raise BadRequestException(
                {"error": _("Post data must be a list of resources.")})
        for obj in data:
            schema = self.schema_class(
                partial=False,
                context=self.schema_context,
                gettext=self.gettext)
            instance, errors = schema.load(obj, self.session)
            if errors is None:
                self.session.add(instance)
            else:
                self.session.rollback()
                raise UnprocessableEntityError(errors)
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise UnprocessableEntityError()

    def put_collection(self, data):
        """Not implemented, not sure how to do this."""
        raise NotImplementedError

    def patch_collection(self, data):
        """Update a collection of resources.

        Individual items may be updated accordingly as part of the
        request as well.

        :param list data: A list of object data. If the object contains
            a key ``$op`` set to ``"add"``, the object will be added to
            the collection; otherwise the object must already be in the
            collection. If ``$op`` is set to ``"remove"``, it is
            accordingly removed from the collection.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: `None`

        """
        _ = self.gettext
        if not isinstance(data, list):
            raise BadRequestException(
                {"error": _("Patch data must be a list of resources.")})
        for obj in data:
            if obj.get("$op") == "add":
                schema = self.schema_class(
                    partial=False,
                    context=self.schema_context,
                    gettext=self.gettext)
                instance, errors = schema.load(obj, self.session)
                if errors is None:
                    self.session.add(instance)
                else:
                    self.session.rollback()
                    raise UnprocessableEntityError(errors)
            elif obj.get("$op") == "remove":
                schema = self.schema_class(
                    partial=True,
                    context=self.schema_context,
                    gettext=self.gettext)
                instance, errors = schema.load(obj, self.session)
                if errors is None:
                    self.session.remove(instance)
                else:
                    self.session.rollback()
                    raise UnprocessableEntityError(errors)
            else:
                schema = self.schema_class(
                    partial=True,
                    context=self.schema_context,
                    gettext=self.gettext)
                instance, errors = schema.load(obj, self.session)
                if errors is not None:
                    self.session.rollback()
                    raise UnprocessableEntityError(errors)
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise UnprocessableEntityError()
        return

    def delete_collection(self, filters=None, session=None):
        """Delete all filter matching members of the collection.

        :param filters: MQLAlchemy style filters.
        :type filters: dict or None
        :param session: See :meth:`get` for more info.
        :type session: :class:`~sqlalchemy.orm.session.Session` or
            :class:`~sqlalchemy.orm.query.Query`
        :return: `None`

        """
        _ = self.gettext
        if filters is None:
            filters = {}
        if session is None:
            session = self.session
        schema, query = self._get_schema_and_query(
            session=session,
            filters=filters)
        query.delete()
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise UnprocessableEntityError()


class ModelResource(with_metaclass(ModelResourceMeta, BaseModelResource)):
    __doc__ = BaseModelResource.__doc__
