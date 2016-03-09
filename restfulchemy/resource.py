from marshmallow.compat import with_metaclass
from mqlalchemy import apply_mql_filters, InvalidMQLException
from mqlalchemy.utils import dummy_gettext
from restfulchemy import resource_class_registry
from restfulchemy.fields import EmbeddedField, NestedRelated
from restfulchemy.query_builder import (
    apply_load_options, apply_sorts, apply_offset_and_limit, SortInfo)


class UnprocessableEntityError(Exception):
    pass


class BadRequestException(Exception):
    pass


class ResourceNotFoundError(Exception):
    pass


class ResourceABC(object):

    def get(self, ident, fields, embeds, parent=None,
            parent_relationship=None, strict=True):
        raise NotImplementedError

    def put(self, ident, data):
        raise NotImplementedError

    def patch(self, ident, data):
        raise NotImplementedError

    def post(self, data):
        raise NotImplementedError

    def delete(self, ident):
        raise NotImplementedError

    def get_collection(self, filters=None, fields=None, embeds=None,
                       sorts=None, offset=None, limit=None, parent=None,
                       parent_relationship=None, strict=True):
        raise NotImplementedError

    def put_collection(self, data):
        raise NotImplementedError

    def patch_collection(self, data):
        raise NotImplementedError

    def post_collection(self, data):
        raise NotImplementedError

    def delete_collection(self, data):
        raise NotImplementedError


class ModelResourceOpts(object):

    def __init__(self, meta):
        self.schema_class = getattr(meta, "schema_class", None)


class ModelResourceMeta(type):

    def __new__(mcs, name, bases, attrs):
        klass = super(ModelResourceMeta, mcs).__new__(mcs, name, bases, attrs)
        meta = getattr(klass, 'Meta')
        klass.opts = klass.OPTIONS_CLASS(meta)
        return klass

    def __init__(self, name, bases, attrs):
        # self is the class obj
        super(ModelResourceMeta, self).__init__(name, bases, attrs)
        resource_class_registry.register(name, self)


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

    # TODO - Handle schema context
    def __init__(self, db_session, schema_context=None, page_max_size=None,
                 gettext=None):
        self._page_max_size = page_max_size
        self._schema_context = schema_context
        self._db_session = db_session
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

        """
        split_keys = key.split(".")
        schema = self.schema_class()
        for i, key in enumerate(split_keys):
            if key in schema.fields:
                field = schema.fields[key]
                if field.load_only:
                    return False
                elif isinstance(field, EmbeddedField):
                    field.embed()
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

        :param key: Name of the field as it was serialized.

        """
        schema = self.schema_class(context=self.schema_context)
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
                    field.embed()
                    if hasattr(field.active_field, "schema"):
                        schema = field.active_field.schema
                if hasattr(field, "schema"):
                    schema = field.schema
            else:
                # Invalid key name, no matching field found.
                return None
        return ".".join(result_keys)

    @property
    def db_session(self):
        """Get a db session to use for this request."""
        if callable(self._db_session):
            return self._db_session()
        else:
            return self._db_session

    @property
    def page_max_size(self):
        """Get the max number of resources to return."""
        if callable(self._page_max_size):
            return self._page_max_size()
        else:
            return self._page_max_size

    @property
    def schema_context(self):
        if callable(self._schema_context):
            return self._schema_context()
        else:
            return self._schema_context

    def _get_ident_filters(self, ident):
        """Generate MQLAlchemy filters using a resource identity."""
        filters = {}
        if not (isinstance(ident, tuple) or
                isinstance(ident, list)):
            ident = (ident,)
        schema = self.schema_class(context=self.schema_context)
        for i, field_name in enumerate(schema.id_keys):
            field = schema.fields.get(field_name)
            filter_name = field.dump_to or field_name
            filters[filter_name] = ident[i]
        return filters

    def _get_instance(self, ident):
        """Given an identity, get the associated SQLAlchemy instance."""
        filters = self._get_ident_filters(ident)
        query = self.db_session.query(self.model)
        query = apply_mql_filters(
            query,
            model_class=self.model,
            filters=filters,
            whitelist=self.whitelist,
            stack_size_limit=100,
            convert_key_names_func=self.convert_key_name,
            gettext=self.gettext)
        return query.first()

    def _get_schema_and_query(self, db_session, filters, fields=None,
                              embeds=None, parent=None,
                              parent_relationship=None, strict=True):
        """Used to generate a schema and query for this request."""
        _ = self.gettext
        query = db_session.query(self.model)
        if parent is not None:
            query = query.with_parent(parent, parent_relationship)
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
                context=self.schema_context)
        else:
            schema = self.schema_class(context=self.schema_context)
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

    def get(self, ident, fields, embeds, parent=None,
            parent_relationship=None, strict=True):
        """Return an individual instance of this resource."""
        _ = self.gettext
        filters = {}
        if not (isinstance(ident, tuple) or
                isinstance(ident, list)):
            ident = (ident,)
        schema = self.schema_class(context=self.schema_context)
        for i, field_name in enumerate(schema.id_keys):
            field = schema.fields.get(field_name)
            filter_name = field.dump_to or field_name
            filters[filter_name] = ident[i]
        schema, query = self._get_schema_and_query(
            self.db_session, filters, fields, embeds, parent,
            parent_relationship, strict)
        instance = query.first()
        if instance is not None:
            return schema.dump(instance).data
        else:
            raise ResourceNotFoundError(_("Resource not found."))

    def delete(self, ident):
        """Remove a resource."""
        _ = self.gettext
        instance = self._get_instance(ident)
        if instance:
            self.db_session.remove(instance)
            self.db_session.commit()
        else:
            raise ResourceNotFoundError(_("Resource not found."))

    def post(self, data):
        """Create a new object and store it in the db."""
        schema = self.schema_class(partial=False, context=self.schema_context)
        instance, errors = schema.load(data, session=self.db_session)
        if errors:
            self.db_session.rollback()
            raise UnprocessableEntityError(errors)
        else:
            self.db_session.add(instance)
            self.db_session.commit()
            return schema.dump(instance).data

    def put(self, ident, data):
        """Replace the current object with the supplied one."""
        obj = data
        instance = self._get_instance(ident)
        schema = self.schema_class(partial=False, instance=instance,
                                   context=self.schema_context)
        instance, errors = schema.load(
            obj, session=self.db_session)
        if errors:
            self.db_session.rollback()
            raise UnprocessableEntityError(errors)
        if instance:
            self.db_session.commit()
            return schema.dump(instance).data

    def patch(self, ident, data):
        """Update an object with new values."""
        obj = data
        instance = self._get_instance(ident)
        schema = self.schema_class(partial=True, instance=instance,
                                   context=self.schema_context)
        instance, errors = schema.load(
            obj, session=self.db_session)
        if errors:
            self.db_session.rollback()
            raise UnprocessableEntityError(errors)
        if instance:
            self.db_session.commit()
            return schema.dump(instance).data

    def get_collection(self, filters=None, fields=None, embeds=None,
                       sorts=None, offset=None, limit=None, parent=None,
                       parent_relationship=None, strict=True):
        """Get a collection of resources.

        :param filters: MQLAlchemy filters to be applied on this query.
        :param fields: A list of fields to be included in the result.
        :param embeds: A list of relationships and relationship fields
            to be included in the result.
        :param sorts: A list of :class:`SortInfo` to be applied to this
            query.
        :param offset: Standard SQL offset to be applied to the query.
        :param limit: Standard SQL limit to be applied to the query.
        :param strict: If `True`, will raise an exception when bad
            parameters are passed. If `False`, will quietly ignore any
            bad input and treat it as if none was provided.
        :returns: A list of resources meeting the supplied criteria.
        :raises BadRequestException: Invalid filters, sorts, fields,
            embeds, offset, or limit will result in a raised exception
            if strict is set to `True`.

        """
        # TODO - error codes?
        _ = self.gettext
        if filters is None:
            filters = {}
        schema, query = self._get_schema_and_query(
            self.db_session, filters, fields, embeds, parent,
            parent_relationship, strict)
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
        """Bulk add newly created items to collection."""
        _ = self.gettext
        if not isinstance(data, list):
            raise BadRequestException(
                {"error": _("Post data must be a list of resources.")})
        for obj in data:
            schema = self.schema_class(partial=False,
                                       context=self.schema_context)
            instance, errors = schema.load(obj, self.db_session)
            if errors is None:
                self.db_session.add(instance)
            else:
                self.db_session.rollback()
                raise UnprocessableEntityError(errors)
        self.db_session.commit()
        # TODO - return number of resources created?

    def patch_collection(self, data):
        """Update a collection with additions or removals.

        Individual items may be updated accordingly as part of the
        request as well.

        :param data: A list of object data. If the object contains a key
            ``$op`` set to ``"add"``, the object will be added to the
            collection; otherwise the object must already be in the
            collection. If ``$op`` is set to ``"remove"``, it is
            accordingly removed from the collection.

        """
        _ = self.gettext
        if not isinstance(data, list):
            raise BadRequestException(
                {"error": _("Patch data must be a list of resources.")})
        for obj in data:
            if obj.get("$op") == "add":
                schema = self.schema_class(partial=False,
                                           context=self.schema_context)
                instance, errors = schema.load(obj, self.db_session)
                if errors is None:
                    self.db_session.add(instance)
                else:
                    self.db_session.rollback()
                    raise UnprocessableEntityError(errors)
            elif obj.get("$op") == "remove":
                schema = self.schema_class(partial=True,
                                           context=self.schema_context)
                instance, errors = schema.load(obj, self.db_session)
                if errors is None:
                    self.db_session.remove(instance)
                else:
                    self.db_session.rollback()
                    raise UnprocessableEntityError(errors)
            else:
                schema = self.schema_class(partial=True,
                                           context=self.schema_context)
                instance, errors = schema.load(obj, self.db_session)
                if errors is not None:
                    self.db_session.rollback()
                    raise UnprocessableEntityError(errors)
        self.db_session.commit()
        # TODO - maybe return a message here with # resources updated?
        return

    def put_collection(self, data, strict=True):
        """TODO - No idea how to handle this..."""
        pass

    def delete_collection(self, filters=None, strict=True):
        pass


class ModelResource(with_metaclass(ModelResourceMeta, BaseModelResource)):
    __doc__ = BaseModelResource.__doc__
