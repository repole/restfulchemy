"""
    restfulchemy.schema
    ~~~~~~~~~~~~~~~~~~~

    Functions for parsing query info from url parameters.

    :copyright: (c) 2016 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from collections import namedtuple
from mqlalchemy import InvalidMQLException
from mqlalchemy.utils import dummy_gettext
import json

SortInfo = namedtuple('SortInfo', 'attr direction')
OffsetLimitInfo = namedtuple('OffsetLimitInfo', "offset limit")


class OffsetLimitParseError(Exception):
    """Generic exception class for query parsing errors."""
    pass


class InvalidSortInfoException(Exception):
    """Generic exception class for invalid sort info applying."""
    pass


def parse_fields(query_params, fields_query_name="fields"):
    """Parse from query params the fields to include in the response.

    :param query_params: Dictionary in which a list of fields may
        be specified for return.
    :param fields_query_name: The name of the key used to check for
        fields in the provided query_params.
    :returns: A list of fields to be included in the response.

    """
    fields = query_params.get(fields_query_name)
    if fields:
        return fields.split(",")
    else:
        return []


def parse_embeds(query_params, embeds_query_name="embeds"):
    """Parse subresource embeds from query params.

    :param query_params: Dictionary in which a list of embedded fields
        may be specified.
    :param embeds_query_name: The name of the key used to check for
        an embed in the provided query_params.
    :returns: A list of embeds to include in the response.

    """
    embeds = query_params.get(embeds_query_name)
    if embeds:
        return embeds.split(",")
    else:
        return []


def parse_offset_limit(query_params, page_max_size=None,
                       page_query_name="page", offset_query_name="offset",
                       limit_query_name="limit", strict=True,
                       gettext=None):
    """Parse offset and limit from the provided query params.

    :param query_params: A dictionary in which a limit or offset may
        be specified.
    :param page_max_size: If page is provided, `page_max_size` limits
        the number of results returned. Otherwise, if using limit and
        offset values from the `query_paras`, `page_max_size` sets a
        max number of records to allow.
    :param page_query_name: The name of the key used to check for a page
        value in the provided `query_params`. If page is provided, it is
        used along with the `page_max_size` to determine the offset that
        should be applied to the query. If a page number other than 1
        is provided, a `page_max_size` must also be provided.
    :param offset_query_name: The name of the key used to check for an
        offset value in the provided `query_params`.
    :param limit_query_name: The name of the key used to check for a
        limit value in the provided `query_params`.
    :param strict: If `True`, exceptions will be raised for invalid
        input. Otherwise, invalid input will be ignored.
    :param gettext: Optional function to be used for any potential
        error translation.
    :raises OffsetLimitParseError: Applicable if using strict mode
        only. If the provided limit is greater than page_max_size, or an
        invalid page, offset, or limit value is provided, then a
        :exc:`OffsetLimitParseError` is raised.
    :returns: An offset and limit value for this query.
    :rtype: :class:`OffsetLimitInfo`

    """
    if gettext is None:
        gettext = dummy_gettext
    _ = gettext
    if query_params is None:
        query_params = {}
    # parse limit
    limit = page_max_size
    if limit_query_name is not None:
        if query_params.get(limit_query_name):
            try:
                limit = int(query_params.get(limit_query_name))
            except ValueError:
                if strict:
                    raise OffsetLimitParseError(
                        _("Provided limit must be an integer."))
    # parse page
    page = query_params.get(page_query_name, None)
    if page is not None:
        try:
            page = int(page)
        except ValueError:
            raise OffsetLimitParseError(
                _("The page value provided (%(page)s) can not be converted to "
                  "an integer.",
                  page=page))
        if page > 1 and page_max_size is None and limit is None:
            if strict:
                raise OffsetLimitParseError(
                    _("Page greater than 1 provided without a page max size."))
            else:
                page = None
        if page < 1:
            if strict:
                raise OffsetLimitParseError(
                    _("Page number can not be less than 1."))
            else:
                page = None
    # defaults
    offset = 0
    if offset_query_name is not None:
        if query_params.get(offset_query_name):
            try:
                offset = int(query_params.get(offset_query_name))
            except ValueError:
                if strict:
                    raise OffsetLimitParseError(
                        _("Provided offset must be an integer."))
    if page_max_size and limit > page_max_size:
        # make sure an excessively high limit can't be set
        if strict:
            raise OffsetLimitParseError(
                _("Provided limit may not be higher than the max page size."))
        limit = page_max_size
    if page is not None and page > 1:
        if limit is not None and page_max_size is None:
            page_max_size = limit
        offset = (page - 1) * page_max_size
    return OffsetLimitInfo(limit=limit, offset=offset)


def parse_sorts(query_params, sort_query_name="sort"):
    """Parse sorts from provided the query params.

    :param query_params: A dictionary in which sorts may be specified.
    :param sort_query_name: The name of the key used to check for sorts
        in the provided `query_params`.
    :returns: A list of :class:`SortInfo`

    """
    result = []
    if sort_query_name in query_params:
        sort_string = query_params[sort_query_name]
        split_sorts = sort_string.split(",")
        for sort in split_sorts:
            direction = "ASC"
            attr_name = sort
            if sort.startswith("-"):
                attr_name = sort[1:]
                direction = "DESC"
            result.append(SortInfo(attr=attr_name, direction=direction))
    return result


def parse_filters(model_class, query_params, complex_query_name="query",
                  only_parse_complex=False, convert_key_names_func=str,
                  strict=True, gettext=None):
    """Convert request params into MQLAlchemy friendly search.

    :param model_class: The SQLAlchemy class being queried.
    :param query_params: A dict of query params in which filters may be
        supplied.
    :param complex_query_name: The name of the key used to check for a
        complex query value in the provided `query_params`. Note that
        the complex query should be a json dumped dictionary value.
    :param only_parse_complex: Set to `True` if all simple filters in
        the query params should be ignored.
    :param convert_key_names_func: If provided, should take in a dot
        separated attr name and transform it such that the result is
        the corresponding dot separated attribute in the `model_class`
        being queried.
        Useful if, for example, you want to allow users to provide an
        attr name in one format (say camelCase) and convert it to the
        naming format used for your model objects (likely underscore).
    :param strict: If `True`, exceptions will be raised for invalid
        input. Otherwise, invalid input will be ignored.
    :param gettext: Optionally may provide a gettext function to handle
        error message translations.
    :raises InvalidMQLException: Malformed complex queries or
        invalid `query_params` will result in an InvalidMQLException
        being raised if `strict` is `True`.
    :returns: A dictionary containing filters that can be passed
        to mqlalchemy for query filtering.

    """
    if gettext is None:
        gettext = dummy_gettext
    _ = gettext
    if query_params is None:
        query_params = {}
    if not isinstance(query_params, dict):
        if strict:
            raise InvalidMQLException(_("Invalid filters provided."))
        else:
            # treat as if none were supplied.
            return {}
    # use an $and query to enable multiple queries for the same
    # attribute.
    result = {"$and": []}
    for key in query_params.keys():
        if key == complex_query_name:
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
                    if strict:
                        raise InvalidMQLException(
                            _("The complex filters query value must be set "
                              "to a valid json dict."))
        elif not only_parse_complex:
            # how much to remove from end of key to get the attr_name.
            # default values:
            chop_len = 0
            attr_name = key
            comparator = "$eq"
            if key.endswith("-gt"):
                chop_len = 3
                comparator = "$gt"
            elif key.endswith("-gte"):
                chop_len = 4
                comparator = "$gte"
            elif key.endswith("-eq"):
                chop_len = 3
                comparator = "$eq"
            elif key.endswith("-lte"):
                chop_len = 4
                comparator = "$lte"
            elif key.endswith("-lt"):
                chop_len = 3
                comparator = "$lt"
            elif key.endswith("-ne"):
                chop_len = 3
                comparator = "$ne"
            elif key.endswith("-like"):
                chop_len = 5
                comparator = "$like"
            if chop_len != 0:
                attr_name = key[:(-1 * chop_len)]
            attr_check = None
            try:
                c_attr_name = convert_key_names_func(attr_name)
                if c_attr_name:
                    attr_check = c_attr_name.split(".")
                    if attr_check:
                        attr_check = attr_check[0]
                    else:
                        attr_check = None
            except AttributeError:
                attr_check = None
            if attr_check is not None and hasattr(model_class, attr_check):
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
