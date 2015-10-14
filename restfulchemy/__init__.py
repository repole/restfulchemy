## -*- coding: utf-8 -*-\
"""
    restfulchemy.__init__
    ~~~~~~~~~~~~~~~~~~~~~

    Utility functions for building a RESTful API around SQLAlchemy.

    :copyright: (c) 2015 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
from restfulchemy._compat import str
from mqlalchemy import convert_to_alchemy_type, apply_mql_filters, \
    InvalidMQLException
from sqlalchemy import literal
from sqlalchemy.orm import ColumnProperty, RelationshipProperty, \
    class_mapper
from sqlalchemy.types import BOOLEAN
from sqlalchemy.inspection import inspect
import json

__version__ = "0.3.0dev"

_ = str


class AlchemyUpdateException(Exception):
    """Generic exception class for invalid updates."""
    pass


def get_full_attr_name(attr_name_stack, short_attr_name=None):
    """Join the attr_name_stack to get a full attribute name."""
    attr_name = ".".join(attr_name_stack)
    if short_attr_name:
        if attr_name != "":
            attr_name += "."
        attr_name += short_attr_name
    return attr_name


def get_class_attributes(RecordClass, attr_name):
    """Get info about each attr given a dot notation attr name."""
    split_attr_name = attr_name.split(".")
    # We assume the full attr name includes the RecordClass
    # Thus we pop the first name.
    # e.g. RecordClass.prop.subprop becomes prop.subprop
    class_name = split_attr_name.pop(0)
    if class_name != RecordClass.__name__:
        raise AttributeError(
            "Dot notation attribute name must start with the name of " +
            "the model class.")
    class_attrs = []
    root_type = RecordClass
    class_attrs.append(root_type)
    if len(split_attr_name) > 0:
        for attr_name in split_attr_name:
            if (hasattr(root_type, "property") and
                    type(root_type.property) == RelationshipProperty):
                if (attr_name.startswith("$id") or
                        attr_name.startswith("~id") or
                        attr_name.startswith("$new") or
                        attr_name.startswith("~new")):
                    class_attrs.append(inspect(root_type).mapper.class_)
                    continue
                elif (attr_name == "~add" or attr_name == "$add" or
                      attr_name == "~remove" or attr_name == "$remove" or
                      attr_name == "~set" or attr_name == "$set"):
                    class_attrs.append(None)
                    continue
                else:
                    root_type = inspect(root_type).mapper.class_
            # will raise an AttributeError if attr_name not in root_type
            class_attr = getattr(root_type, attr_name)
            root_type = class_attr
            class_attrs.append(class_attr)
    return class_attrs


def parse_filters(RecordClass, query_params, only_parse_complex=False):
    """Convert request params into MQLAlchemy friendly search."""
    if not isinstance(query_params, dict):
        # invalid filters provided, treat as if none were supplied.
        return {}
    # use an $and query to enable multiple queries for the same
    # attribute.
    result = {"$and": []}
    for key in query_params.keys():
        if key == "$query" or key == "~query":
            complex_query_list = []
            if isinstance(query_params[key], list):
                complex_query_list = query_params[key]
            else:
                complex_query_list.append(query_params[key])
            for complex_query in complex_query_list:
                try:
                    query = json.loads(complex_query)
                    if not isinstance(query, dict):
                        raise ValueError()
                    result["$and"].append(query)
                except (TypeError, ValueError):
                    raise InvalidMQLException(
                        key + " must be set to a valid json dumped dict.")
        elif not only_parse_complex:
            # how much to remove from end of key to get the attr_name.
            # default values:
            chop_len = 0
            attr_name = key
            comparator = "$eq"
            if key.endswith("_$gt") or key.endswith("_~gt"):
                chop_len = 4
                comparator = "$gt"
            elif key.endswith("_$gte") or key.endswith("_~gte"):
                chop_len = 5
                comparator = "$gte"
            elif key.endswith("_$eq") or key.endswith("_~eq"):
                chop_len = 4
                comparator = "$eq"
            elif key.endswith("_$lte") or key.endswith("_~lte"):
                chop_len = 5
                comparator = "$lte"
            elif key.endswith("_$lt") or key.endswith("_~lt"):
                chop_len = 4
                comparator = "$lt"
            elif key.endswith("_$ne") or key.endswith("_~ne"):
                chop_len = 4
                comparator = "$ne"
            elif key.endswith("_$like") or key.endswith("_~like"):
                chop_len = 6
                comparator = "$like"
            if chop_len != 0:
                attr_name = key[:(-1 * chop_len)]
            if hasattr(RecordClass, attr_name):
                # ignore any top level invalid params
                value = query_params[key]
                if isinstance(value, list):
                    for item in value:
                        result["$and"].append(
                            {attr_name: {comparator: item}})
                else:
                    result["$and"].append(
                        {attr_name: {comparator: value}})
    if len(result["$and"]) == 0:
        return {}
    return result


def apply_order_by(query, RecordClass, query_params):
    """Given query_params that contain an order_by key, apply sorts.

    Format for order_by is `attr_name~ASC-other_attr~DESC`, where
    hyphens separate order_by statements, and tildes are used to
    denote direction.

    """
    if query_params is None:
        query_params = {}
    order_by_params = query_params.get("~order_by")
    if order_by_params:
        split_order_by_list = order_by_params.split("-")
        for order_by in split_order_by_list:
            split_order_by = order_by.split("~")
            if len(split_order_by) > 0 and split_order_by[0]:
                direction = "ASC"
                if (len(split_order_by) > 1 and
                        split_order_by[1].lower().startswith("d")):
                    direction = "DESC"
                attr_name = split_order_by[0]
                if hasattr(RecordClass, attr_name):
                    if direction == "ASC":
                        query = query.order_by(
                            getattr(RecordClass, attr_name).asc())
                    else:
                        query = query.order_by(
                            getattr(RecordClass, attr_name).desc())
    return query


def apply_offset_and_limit(query, query_params, page=None, page_max_size=None):
    """Applies offset and limit to the query if appropriate.

    :param query: Any desired filters must already have been applied.
    :param query_params: A dictionary in which "$limit", "~limit",
                         "$offset", or "~offset" may be supplied.
    :param page: If provided, is used along with the page_max_size to
                 determine the offset that should be applied to the
                 query. If a page number other than 1 is provided, a
                 page_max_size must also be provided.
    :param page_max_size: If page is provided, page_max_size limits the
                          number of results returned.
                          Otherwise, if using limit and offset values
                          from the query_params, page_max_size sets a
                          max number of records to allow. If a
                          query_param limit of a higher number is
                          provided, it will be ignored.

    """
    if query_params is None:
        query_params = {}
    if page is not None:
        if page > 1 and page_max_size is None:
            raise ValueError(
                "A page greater than 1 is provided without a page_max_size.")
        if page < 1:
            raise ValueError("Page number can not be less than 1.")
    # defaults
    offset = 0
    limit = page_max_size
    for param_key in ["$offset", "~offset"]:
        if query_params.get(param_key):
            try:
                offset = int(query_params.get(param_key))
            except ValueError:
                pass
    for param_key in ["$limit", "~limit"]:
        if query_params.get(param_key):
            try:
                limit = int(query_params.get(param_key))
            except ValueError:
                pass
    if page_max_size and limit > page_max_size:
        # make sure an excessively high limit can't be set
        limit = page_max_size
    if page is not None and page > 1:
        offset = (page - 1) * page_max_size
    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)
    return query


def _get_whitelist_name(name_stack):
    """Returns a joined name_stack, but removes $new and $id."""
    names = []
    for attr in name_stack:
        if attr.startswith(("$new", "~new", "_new_")):
            attr = "$new"
        elif attr.startswith(("$id", "~id", "_id_")):
            attr = "$id"
        names.append(attr)
    return ".".join([str(name) for name in names])


def _cleanse_update_params(instance, query_params):
    """Get a cleaned set of query params with only valid update keys.

    If you want to use func:`update_object` with some query params
    passed in via a server request, this function will attempt to
    parse out any unnecessary or invalid parameters from that set of
    query params and returns a new dictionary with only valid keys.

    """
    if query_params is None:
        query_params = {}
    result = {}
    for key in query_params.keys():
        # if the first part of the key is an attribute of our
        # base instance object, then assume this is an attribute
        # we are trying to update. Otherwise, ignore it.
        # Note that this may get tricky for general params like
        # page if they happen to also exist as an attr in instance,
        # and in these cases they need to be removed or handled
        # appropriately in the query string prior to using this
        # function.
        split_name = key.split('.')
        if split_name and hasattr(instance, split_name[0]):
            result[key] = query_params[key]
    return result


def _split_dict_params(update_params):
    """Split dot notation query params into a hierarchical dict.

    {"friend.user_id": 5} becomes {"friend": {"user_id": 5}}

    """
    result = {}
    for key in update_params.keys():
        split_name = key.split('.')
        name_stack = list()
        for prop_name in split_name:
            sub_result = result
            for name in name_stack:
                if name not in sub_result:
                    sub_result[name] = {}
                sub_result = sub_result[name]
            name_stack.append(prop_name)
            # both sub_result and prop_name are guaranteed to be set
            # since we check if split_name is empty in the initial
            # if statement.
        sub_result[prop_name] = update_params[key]
    return result


def _filter_by_primary_key(query, RecordClass, primary_key_names,
                           primary_key_data, full_attr_name, error_dict, _):
    """Generate a query that filters on primary key value(s)."""
    for primary_key_name in primary_key_names:
        if primary_key_name in primary_key_data:
            primary_key_attr = getattr(RecordClass, primary_key_name)
            try:
                primary_key_value = convert_to_alchemy_type(
                    primary_key_data[primary_key_name],
                    type(primary_key_attr.type))
            except (TypeError, ValueError):
                _append_error(
                    error_dict,
                    full_attr_name,
                    _("Invalid $id primary key value."))
                return None
            query = query.filter(primary_key_attr == primary_key_value)
        else:
            _append_error(
                error_dict,
                full_attr_name,
                _("Invalid $id primary key field."))
            return None
    return query


def get_alchemy_primary_keys(RecordClass):
    """Get a list of primary key fields for a SQLAlchemy class."""
    primary_keys = []
    for prop in class_mapper(RecordClass).iterate_properties:
        if isinstance(prop, ColumnProperty):
            for primary_key in class_mapper(RecordClass).primary_key:
                if prop.columns:
                    if prop.columns[0].compare(primary_key):
                        primary_keys.append(prop.key)
    return primary_keys


def get_primary_key_dict(id_string):
    """Turns "$id:some_field=6" into {"some_field": 6}."""
    # TODO - Handle escape chars.
    # TODO - Better error handling.
    split_string = id_string.split(":")
    # remove the $id portion of the string
    split_string.pop(0)
    result = {}
    for key_value in split_string:
        split_key_value = key_value.split("=")
        result[split_key_value[0]] = split_key_value[1]
    return result


def _set_non_list_relationship_obj(relation_obj, parent, relationship_name,
                                   update_stack_item, full_attr_name,
                                   whitelist_name, whitelist, error_dict,
                                   validation_mode, _):
    """Set a non list using relationship to a given object."""
    if getattr(parent, relationship_name) is not None:
        if not (isinstance(update_stack_item, dict) and (
                update_stack_item.get("$set") in (
                    True, "True", "true", 1, "1") or
                update_stack_item.get("~set") in (
                    True, "True", "true", 1, "1"))):
            _append_error(
                error_dict,
                full_attr_name,
                _("Referenced a sub item $id that does not exist." +
                  "Did you forget to include $set for this sub item?"))
            return False
        if not (_is_whitelisted(whitelist_name, whitelist, "set") or
                (_is_whitelisted(whitelist_name, whitelist, "remove") and
                 _is_whitelisted(whitelist_name, whitelist, "add"))):
            _append_error(
                error_dict,
                full_attr_name,
                _("Can not set this relation to a different object. " +
                  "The relationship is already set to another object and " +
                  "neither $set nor $remove and $add are whitelisted."))
            return False
        if not validation_mode:
            setattr(parent, relationship_name, relation_obj)
        return True
    else:
        if not (isinstance(update_stack_item, dict) and (
                update_stack_item.get("$set") in (
                    True, "True", "true", 1, "1") or
                update_stack_item.get("~set") in (
                    True, "True", "true", 1, "1") or
                update_stack_item.get("$add") in (
                    True, "True", "true", 1, "1") or
                update_stack_item.get("~add") in (
                    True, "True", "true", 1, "1"))):
            _append_error(
                error_dict,
                full_attr_name,
                _("Referenced a sub item $id that does not exist. " +
                  "Did you forget to include $set or $add for this sub item?"))
            return False
        if not (_is_whitelisted(whitelist_name, whitelist, "add") or
                _is_whitelisted(whitelist_name, whitelist, "set")):
            _append_error(
                error_dict,
                full_attr_name,
                _("Can not set this relation to a different object. " +
                  "Neither $set nor $add are whitelisted."))
            return False
        if not validation_mode:
            setattr(parent, relationship_name, relation_obj)
        return True


def create_resource(db_session, RecordClass, params, whitelist=None,
                    add_to_session=True, stack_size_limit=None):
    """Create a new instance of a SQLAlchemy object.

    See :func:`update_object` for parameter details.
    The only difference between this function and :func:`update_object`
    is a new object is created and returned rather than being supplied.

    """
    instance = RecordClass()
    _set_record_attrs(
        db_session,
        instance,
        _cleanse_update_params(instance, params),
        whitelist,
        add_to_session,
        stack_size_limit
    )
    if add_to_session:
        db_session.add(instance)
    return instance


def get_resources_query(db_session, RecordClass, query_params, whitelist=None,
                        stack_size_limit=None):
    """Get a query object with filters from query_params applied.

    :param db_session: A SQLAlchemy database session or query session.
    :param RecordClass: The SQLAlchemy model class you want to query.
    :param query_params: A dictionary of query parameters that came in
                         with a web request. In Flask, you probably want
                         to pass in `request.values.to_dict()`. In
                         CherryPy you'd pass in `request.params`.
                         Any top level parameters will be considered
                         part of an $and statement. So
                         example.com?name=Nick&age=25 would query
                         for a person who's name is Nick and is 25.
                         You can also have a more complex $query
                         argument that contains a json dumped string
                         or dictionary of potentially more complex
                         query parameters. These parameters follow
                         the format specified in MQLAlchemy, similar
                         to a MongoDB query. See
                         :func:`mqlalchemy.apply_mql_filters` for more
                         info.
    :param whitelist: A list of object attributes that are acceptable
                      to query. See :func:`mqlalchemy.apply_mql_filters`
                      for more info.
    :param stack_size_limit: A way of limiting how complex of a query is
                             allowable.
                             See :func:`mqlalchemy.apply_mql_filters`
                             for more info.

    """
    filters = parse_filters(RecordClass, query_params)
    query = apply_mql_filters(
        db_session,
        RecordClass,
        filters,
        whitelist,
        stack_size_limit)
    return query


def get_resources(db_session, RecordClass, query_params, whitelist=None,
                  page=None, page_max_size=None, stack_size_limit=None):
    """Get a list of SQLAlchemy objects.

    See :func:`get_resources_query` and :func:`apply_order_by` for
    details on the parameters.

    """
    query = get_resources_query(
        db_session,
        RecordClass,
        query_params,
        whitelist,
        stack_size_limit
    )
    query = apply_order_by(query, RecordClass, query_params)
    query = apply_offset_and_limit(query, query_params, page, page_max_size)
    return query.all()


def get_resource(db_session, RecordClass, query_params, whitelist=None,
                 stack_size_limit=None):
    """Get a single instance of a SQLAlchemy object.

    See :func:`get_resources_query` and :func:`apply_order_by` for
    details on the parameters. The main difference between this function
    and :func:`get_resources` is this one calls `first()` on the query
    object rather than `all()`.

    """
    query = get_resources_query(
        db_session,
        RecordClass,
        query_params,
        whitelist,
        stack_size_limit
    )
    query = apply_order_by(query, RecordClass, query_params)
    query = apply_offset_and_limit(query, query_params, None, 1)
    return query.first()


def update_resource(db_session, instance, params, whitelist=None,
                    add_to_session=True, stack_size_limit=None):
    """Update a SQLAlchemy model instance based on query params.

    To update a relationship item, regardless of if the relationship
    uses a list or not, you must use $id notation::

        update_resource(
            db_session,
            album,
            {"artist.$id:artist_id=1.name": "Nas"}
            whitelist=["artist.name"])

    This would update the provided album's artist name to "Nas".
    Note that this probably isn't what you want to do, but
    rather want to set the album's artist relation to a
    different artist object. To do this, you would write::

        update_resource(
            db_session,
            album,
            {"artist.$id:artist_id=5.$add": True}
            whitelist=["artist.$add", "artist.$remove"])

    The `"artist.$add"` allows setting the album.artist relationship
    to a artist that already exists in the database. For a relationship
    that doesn't use a list, setting the relation to a different object
    implicitly results in the old object (if one exists) to be removed
    from the parent, thus we must include `"artist.$remove"` in the
    whitelist. You may also use $set instead to enable both $add and
    $remove for a non list using relationship.

    Relationships that use lists work slightly differently, as
    including an $id that isn't already in the list will simply result
    in adding that object, but won't result in any others being removed.

    To explicitly remove an object from a relation::

        update_resource(
            db_session,
            album,
            {"artist.$id:artist_id=1.$remove": True}
            whitelist=["artist.$remove"])

    In this case, since the `artist` relationship does not use a list,
    `album.artist` would simply be set to `None`. If the relationship
    was a list, the artist with a matching $id would simply be removed
    from the relationship list.


    :param params: A dictionary of dot notation attribute names
                   that are to be updated.
                   friends.$new0.user_id would denote creating
                   a new friend in the friends relationship
                   and assigning the user_id attribute. Any
                   other params that start with friend.$new0
                   would denote an attribute assignment on that
                   same new object.
    :param whitelist: A whitelist of attributes that are allowed to be
                      set.

                      Special rules for relationships, using
                      :class:`Playlist` as a reference:

                      * tracks.$create
                          Allows the creation of a new track (using
                          the above mentioned $new notation). Whitelist
                          must also include $add or (for non list using
                          relationships) $set to allow this item to
                          actually be added to the relationship.
                      * tracks.$add
                          Enables appending to the relationship a
                          pre-existing track. So if your
                          update_params includes a field
                          "tracks.$id:track_id=5.$add" set equal to a
                          True expression, and a track with id equal
                          to 5 already exists, that track will be
                          added to album.tracks.
                      * tracks.$remove
                          Enables removing an object from a
                          relationship.
                          "tracks.$id:track_id=5.$remove" set equal
                          to a True expression will result in
                          removing the track with id equal to 5
                          from this relationship.
                      * tracks
                          If you include simply the name of the
                          relationship in the whitelist,
                          $create, $remove, $add, and $set are all
                          enabled.

    :param add_to_session: Defaults to `True`, determines whether
                           newly created objects are automatically
                           added to the database session.

    """
    _set_record_attrs(
        db_session,
        instance,
        _cleanse_update_params(instance, params),
        whitelist,
        add_to_session,
        stack_size_limit)


def _is_whitelisted(whitelist_name, whitelist, verb=None):
    """Return true if whitelist_name is in whitelist.

    :param verb: "add", "remove", "create", or "set".

    """
    if whitelist is None:
        return True
    if isinstance(whitelist, list):
        short_whitelist_name = whitelist_name
        for attr in ["$id", "$new"]:
            short_whitelist_name = short_whitelist_name.replace("." + attr, "")
        if whitelist_name in whitelist or short_whitelist_name in whitelist:
            return True
        if verb is not None:
            money_notation = ".$" + str(verb)
            if whitelist_name + money_notation in whitelist:
                return True
            elif short_whitelist_name + money_notation in whitelist:
                return True
    return False


def _append_to_list_relation(relation_obj, parent, update_stack_item,
                             full_attr_name, whitelist_name, whitelist,
                             error_dict, validation_mode=False, _=str):
    """Add an object to a list relation."""
    if not (isinstance(update_stack_item, dict) and (
            update_stack_item.get("$add") in (
                True, "True", "true", 1, "1") or
            update_stack_item.get("~add") in (
                True, "True", "true", 1, "1"))):
        _append_error(
            error_dict,
            full_attr_name,
            _("This sub-item is not currently included in this " +
              "relationship. Were you attempting to add a new item and "
              "forgot to include an $add field?"))
        return False
    if not _is_whitelisted(whitelist_name, whitelist, "add"):
        _append_error(
            error_dict,
            full_attr_name,
            _("Adding an object to this relation is not whitelisted"))
        return False
    if not validation_mode:
        parent.append(relation_obj)
    return True


def _append_error(error_dict, field_name, message):
    """Appends the provided error message to a dictionary."""
    if not isinstance(error_dict.get(field_name), list):
        error_dict[field_name] = list()
    error_dict[field_name].append(message)


def _set_record_attrs(db_session, instance, params, whitelist=None,
                      add_to_session=True, stack_size_limit=None,
                      validation_mode=False):
    """Set a SQLAlchemy model instance from a dictionary of params."""
    split_params = _split_dict_params(params)
    # process the newly formatted query params into a series of updates
    update_stack = list()
    update_stack.append(split_params)
    key_stack = list()
    attr_stack = list()
    attr_stack.append(instance)
    error_dict = {}
    while update_stack:
        if stack_size_limit and len(update_stack) > stack_size_limit:
            raise AlchemyUpdateException("This update is too complex.")
        item = update_stack.pop()
        if item == "POP":
            attr_stack.pop()
            key_stack.pop()
        elif len(item.keys()) == 1:
            key = list(item.keys())[0]
            parent = attr_stack[-1]
            # get property types
            prop_name_stack = list(key_stack)
            prop_name_stack.insert(0, type(instance).__name__)
            try:
                class_attrs = get_class_attributes(
                    type(instance),
                    ".".join([str(prop) for prop in prop_name_stack + [key]]))
            except AttributeError:
                _append_error(
                    error_dict,
                    get_full_attr_name(key_stack, key),
                    _("Invalid attribute name."))
                # any operation on this attribute or its children
                # will be invalid so continue to next item in stack.
                continue
            if key in ("$add", "~add", "$set", "~set"):
                # Add an object to a relation.
                # Will have been taken care of by previous $id field.
                # Saying {"Track.$id:TrackId=1.$add": True}
                # is just an explicit way of adding a pre-existing
                # item to a relation without having to set another
                # attribute.
                pass
            elif key == "$remove" or key == "~remove":
                try:
                    should_remove = convert_to_alchemy_type(
                        item[key], BOOLEAN)
                except ValueError:    # pragma no cover
                    # convert_to_alchemy_type should never
                    # fail with BOOLEAN, but just incase...
                    should_remove = False
                if should_remove:
                    whitelist_name = _get_whitelist_name(key_stack)
                    if not _is_whitelisted(whitelist_name, whitelist,
                                           "remove"):
                        _append_error(
                            error_dict,
                            get_full_attr_name(key_stack, key),
                            _("Removing this relation is not allowed."))
                    else:
                        if (len(class_attrs) >= 4 and
                                hasattr(class_attrs[-3], "property") and
                                class_attrs[-3].property.uselist is False):
                            # Delete single entity relationship obj
                            grandparent = attr_stack[-3]
                            # key_stack[-1] should be the key name of the
                            # relationship obj
                            if not validation_mode:
                                setattr(grandparent, key_stack[-2], None)
                            # replace the old parent with None now
                            attr_stack.pop()
                            attr_stack.append(None)
                        elif (len(class_attrs) >= 3 and
                              hasattr(class_attrs[-3], "property") and
                              class_attrs[-3].property.uselist):
                            # Delete relationship obj from list
                            grandparent = attr_stack[-2]
                            if not validation_mode:
                                grandparent.remove(parent)
                        else:    # pragma no cover
                            # failsafe - should never get here due to
                            # convert_to_alchemy_type failing prior
                            _append_error(
                                error_dict,
                                get_full_attr_name(key_stack, key),
                                _("Removing this relation is not a valid "
                                  "action."))
            elif key.startswith("$new") or key.startswith("~new"):
                whitelist_name = _get_whitelist_name(key_stack)
                if not _is_whitelisted(whitelist_name, whitelist, "create"):
                    _append_error(
                        error_dict,
                        get_full_attr_name(key_stack, key),
                        _("You may not create a new instance of this object."))
                elif not isinstance(item[key], dict):    # pragma no cover
                    # failsafe - Should be caught one iteration
                    # before this, near the end of the function.
                    _append_error(
                        error_dict,
                        get_full_attr_name(key_stack, key),
                        _("Attempted to set an object to a raw value."))
                else:
                    if not (len(class_attrs) >= 2 and
                            hasattr(class_attrs[-2],
                                    "property")):    # pragma no cover
                        # failsafe
                        # An invalid $new gets caught in a few places
                        # before here (get_class_attributes and
                        # convert_to_alchemy_type), so it shouldn't be
                        # possible to actually hit this line of code.
                        # Keeping it just incase either of those
                        # functions change.
                        # Just an FYI for anyone running coverage.
                        _append_error(
                            error_dict,
                            get_full_attr_name(key_stack, key),
                            _("Invalid parent for this newly created object."))
                    else:
                        # appending a new object to a list relationship
                        RecordClass = inspect(class_attrs[-2]).mapper.class_
                        sub_instance = RecordClass()
                        if class_attrs[-2].property.uselist:
                            success = _append_to_list_relation(
                                sub_instance,
                                parent,
                                item[key],
                                get_full_attr_name(key_stack, key),
                                whitelist_name,
                                whitelist,
                                error_dict,
                                validation_mode,
                                _)
                        else:
                            success = _set_non_list_relationship_obj(
                                sub_instance,
                                attr_stack[-2],
                                key_stack[-1],
                                item[key],
                                get_full_attr_name(key_stack, key),
                                whitelist_name,
                                whitelist,
                                error_dict,
                                validation_mode,
                                _)
                        if add_to_session and not validation_mode and success:
                            db_session.add(sub_instance)
                        # Even if this operation fails, we push the
                        # new object to the stack for the sake of
                        # continuing forward and checking errors.
                        key_stack.append(key)
                        attr_stack.append(sub_instance)
                        update_stack.append("POP")
                        update_stack.append(item[key])
            elif key.startswith("$id") or key.startswith("~id"):
                if not (len(class_attrs) >= 2 and
                        len(attr_stack) >= 2 and
                        hasattr(
                            class_attrs[-2],
                            "property")):    # pragma no cover
                    # failsafe - Like $new, we should never raise this,
                    # exception since the problem gets caught in two other
                    # functions. Just an FYI for coverage purposes.
                    _append_error(
                        error_dict,
                        get_full_attr_name(key_stack, key),
                        _("Invalid $id reference."))
                else:
                    RecordClass = inspect(class_attrs[-2]).mapper.class_
                    primary_key_names = get_alchemy_primary_keys(RecordClass)
                    primary_key_data = get_primary_key_dict(key)
                    success = False
                    # Note that attr_stack[-1] is the relationship list
                    # So attr_stack[-2] is the actual parent object
                    query = db_session.query(
                        RecordClass).with_parent(attr_stack[-2])
                    query = _filter_by_primary_key(
                        query, RecordClass, primary_key_names,
                        primary_key_data, get_full_attr_name(key_stack, key),
                        error_dict, _)
                    if query is None:
                        # filter by primary key failed
                        relation_obj = None
                    elif db_session.query(
                            literal(True)).filter(query.exists()).scalar():
                        # this obj is already in the relationship
                        relation_obj = query.first()
                        if relation_obj is None:    # pragma no cover
                            # Test coverage: won't hit this - timing issue.
                            _append_error(
                                error_dict,
                                get_full_attr_name(key_stack, key),
                                _("A database race condition caused an " +
                                  "unexpected error. Please try again."))
                        else:
                            success = True
                    else:
                        # this obj is not in the relationship
                        # run actual query to get object
                        query = db_session.query(RecordClass)
                        query = _filter_by_primary_key(
                            query,
                            RecordClass,
                            primary_key_names,
                            primary_key_data,
                            get_full_attr_name(key_stack, key),
                            error_dict,
                            _)
                        if query is None:    # pragma no cover
                            # The prior _filter_by_primary_key will
                            # error out first, making it not possible
                            # to have the above _filter_by_primary_key
                            # fail to build a valid query.
                            # This was left here purely as a fail safe.
                            relation_obj = None
                        else:
                            relation_obj = query.first()
                            if relation_obj is None:    # pragma no cover
                                # coverage won't hit this due to timing.
                                _append_error(
                                    error_dict,
                                    get_full_attr_name(key_stack, key),
                                    _("A database race condition caused an " +
                                      "unexpected error. Please try again."))
                            else:
                                whitelist_name = _get_whitelist_name(key_stack)
                                # Add relationship obj to list
                                if class_attrs[-2].property.uselist:
                                    success = _append_to_list_relation(
                                        relation_obj,
                                        parent,
                                        item[key],
                                        get_full_attr_name(key_stack, key),
                                        whitelist_name,
                                        whitelist,
                                        error_dict,
                                        validation_mode,
                                        _)
                                else:
                                    # want grandparent for non uselist.
                                    # Given album.artist.$id:artist_id=1,
                                    # attr_stack[-2] is album.
                                    success = _set_non_list_relationship_obj(
                                        relation_obj,
                                        attr_stack[-2],
                                        key_stack[-1],
                                        item[key],
                                        get_full_attr_name(key_stack, key),
                                        whitelist_name,
                                        whitelist,
                                        error_dict,
                                        validation_mode,
                                        _)
                    if not isinstance(item[key], dict):
                        _append_error(
                            error_dict,
                            get_full_attr_name(key_stack, key),
                            _("Attempted to set an object to a raw value."))
                    else:
                        if not success:
                            # Use dummy object for further validation
                            relation_obj = RecordClass()
                        key_stack.append(key)
                        attr_stack.append(relation_obj)
                        update_stack.append("POP")
                        update_stack.append(item[key])
            else:
                # TODO - whitelist check
                if parent is None:
                    # failsafe - probably didn't use an $id identifier.
                    _append_error(
                        error_dict,
                        get_full_attr_name(key_stack, key),
                        _("Attribute doesn't have a valid parent object."))
                elif (hasattr(class_attrs[-1], "property") and
                      type(class_attrs[-1].property) == ColumnProperty):
                    # temp operation for whitelist checking,
                    # will be undone below.
                    key_stack.append(key)
                    whitelist_name = _get_whitelist_name(key_stack)
                    if _is_whitelisted(whitelist_name, whitelist):
                        key_stack.pop()
                        target_type = class_attrs[-1].property.columns[0].type
                        error = False
                        try:
                            value = convert_to_alchemy_type(item[key],
                                                            type(target_type))
                        except TypeError:
                            _append_error(
                                error_dict,
                                get_full_attr_name(key_stack, key),
                                _("Unable to convert value to the proper " +
                                  "type."))
                            error = True
                            value = None
                        if not validation_mode and not error:
                            setattr(parent, key, value)
                    else:
                        key_stack.pop()
                        _append_error(
                            error_dict,
                            get_full_attr_name(key_stack, key),
                            _("You do not have permission to modify " +
                              "this attribute."))
                else:
                    # this is some obj property
                    if (hasattr(class_attrs[-1], "property") and not
                            class_attrs[-1].property.uselist):
                        # if this is a relationship that doesn't use
                        # a list, then we append a None obj to the
                        # attr stack to prevent trying to set, for
                        # example, artist.album.some_attr to a
                        # value without using an $id identifier.
                        attr = None
                    else:
                        attr = getattr(parent, key)
                    if isinstance(item[key], dict):
                        attr_stack.append(attr)
                        key_stack.append(key)
                        update_stack.append("POP")
                        update_stack.append(item[key])
                    else:
                        _append_error(
                            error_dict,
                            get_full_attr_name(key_stack, key),
                            _("Attempted to set an object to a raw value."))
        else:
            for key in sorted(item.keys()):
                # we sort to ensure that actions like $add or $remove
                # occur first.
                update_stack.append({key: item[key]})
    if error_dict:
        raise AlchemyUpdateException(error_dict)
    else:
        return instance
