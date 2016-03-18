"""
    restfulchemy.router
    ~~~~~~~~~~~~~~~~~~~

    Tools for automatically routing API url paths to resources.

    Work in progress, should not be used as anything other than
    a proof of concept at this point.

    :copyright: (c) 2016 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from mqlalchemy import convert_to_alchemy_type
from restfulchemy.parser import (
    parse_embeds, parse_fields, parse_filters, parse_offset_limit, parse_sorts)
from restfulchemy.fields import EmbeddedField, RelationshipUrl
from restfulchemy.resource import BadRequestException


def generic_api_router_get(path, api_resource, query_params, strict=True):
    """Generic API router for GET requests.

    :param str path: The resource path specified.
    :param api_resource: A resource instance.
    :type api_resource: :class:`~restfulchemy.resource.ModelResource`
    :param dict query_params: Dictionary of query parameters.
    :param bool strict: If `True`, raise non fatal errors rather
        than ignoring them.
    :return: If this is a single entity query, an individual resource
        or `None`. If this is a collection query, a list of resources.

    """
    split_path = path.split("/")
    # remove empty string if path started with a slash
    if len(split_path) > 0 and split_path[0] == "":
        split_path.pop(0)
    id_keys = api_resource.schema_class().id_keys
    fields = parse_fields(query_params)
    embeds = parse_embeds(query_params)
    if len(split_path) == 1:
        # e.g. /albums/
        filters = parse_filters(
            api_resource.model,
            query_params,
            convert_key_names_func=api_resource.convert_key_name,
            gettext=api_resource.gettext)
        offset, limit = parse_offset_limit(
            query_params,
            api_resource.page_max_size,
            gettext=api_resource.gettext)
        sorts = parse_sorts(
            query_params)
        return api_resource.get_collection(
            filters=filters,
            fields=fields,
            embeds=embeds,
            sorts=sorts,
            offset=offset,
            limit=limit,
            strict=strict)
    elif len(split_path) < (len(id_keys) + 1):
        # e.g. /resource/<key_one_of_two/
        # resource that has a multi key identifier; only one provided
        raise BadRequestException()
    elif len(split_path) == (len(id_keys) + 1):
        # e.g. /albums/<album_id>
        # simple api get
        ident = ()
        for key in split_path[1:(len(id_keys) + 1)]:
            ident = ident + (key, )
        return api_resource.get(
            ident=ident,
            fields=fields,
            embeds=embeds,
            strict=strict)
    else:
        # subresource
        # e.g. /albums/1/tracks or /albums/1/tracks/5
        sub_split_path = split_path[(len(id_keys) + 1):]
        # get the parent obj
        parent_query = api_resource.session.query(api_resource.model)
        for i, id_key in enumerate(id_keys):
            # TODO - error handling here
            model_attr = getattr(api_resource.model, id_key)
            target_type = type(model_attr.property.columns[0].type)
            value = convert_to_alchemy_type(split_path[i+1], target_type)
            parent_query = parent_query.filter(model_attr == value)
        parent = parent_query.first()
        if parent is None:
            # Not found exception
            raise BadRequestException()
        sub_resource_name = api_resource.convert_key_name(sub_split_path[0])
        sub_resource_field = api_resource.schema_class().fields.get(
            sub_resource_name)
        if isinstance(sub_resource_field, EmbeddedField):
            if isinstance(sub_resource_field.default_field, RelationshipUrl):
                sub_resource_api_class = (
                    sub_resource_field.default_field.resource_class)
        # TODO - Error handling here
        sub_resource_api = sub_resource_api_class(
            session=api_resource.session,
            gettext=api_resource.gettext)
        sub_id_keys = sub_resource_api.schema_class().id_keys
        query_session = sub_resource_api.session
        query_session = query_session.query(sub_resource_api.model)
        query_session = query_session.with_parent(parent,
                                                  sub_resource_name)
        if len(sub_split_path) == 1:
            # e.g. /albums/1/tracks
            filters = parse_filters(
                sub_resource_api.model,
                query_params,
                convert_key_names_func=sub_resource_api.convert_key_name,
                gettext=sub_resource_api.gettext)
            offset, limit = parse_offset_limit(
                query_params,
                sub_resource_api.page_max_size,
                gettext=sub_resource_api.gettext)
            sorts = parse_sorts(
                query_params)
            return sub_resource_api.get_collection(
                filters=filters,
                fields=fields,
                embeds=embeds,
                sorts=sorts,
                offset=offset,
                limit=limit,
                session=query_session,
                strict=strict)
        elif len(sub_split_path) < (len(sub_id_keys) + 1):
            # e.g. /albums/1/some_resource/<key_one_of_two>
            # sub resource has a multi key identifier; only one provided
            raise BadRequestException()
        elif len(sub_split_path) == (len(sub_id_keys) + 1):
            # e.g. /albums/1/tracks/3
            # sub resource collection get
            ident = ()
            for key in sub_split_path[1:(len(sub_id_keys) + 1)]:
                ident = ident + (key, )
            return sub_resource_api.get(
                ident=ident,
                fields=fields,
                embeds=embeds,
                strict=strict,
                session=query_session)
        else:
            raise BadRequestException()


def generic_api_router(method, path, api_resource, query_params, data=None,
                       content_type="json", strict=True):
    """Route requests based on path and resource.

    :param str path: The resource path specified. This should not include
        the root ``/api`` or any versioning info.
    :param api_resource: An already initialized resource instance.
    :type api_resource: :class:`~restfulchemy.resource.ResourceABC`
    :param dict query_params: Dictionary of query parameters, likely
        provided as part of a request.
    :param bool strict: If `True`, faulty pagination info, fields, or
        embeds will result in an error being raised rather than
        silently ignoring them.

    """
    if method.toLower() == "GET":
        return generic_api_router_get(path, api_resource, query_params, strict)
    else:
        # TODO - Finish this!
        raise BadRequestException("Method not available.")
