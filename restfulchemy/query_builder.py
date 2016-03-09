from restfulchemy.parser import SortInfo
from mqlalchemy.utils import dummy_gettext
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import joinedload, RelationshipProperty


def apply_sorts(query, sorts, convert_key_names_func=str):
    """Apply sorts to a provided query.

    :param query: A SQLAlchemy query; filters must already have been
        applied.
    :param sorts: A list of sorts to apply to this query.
    :param convert_key_names_func: See :func:`parse_filters`.
    :type sorts: List of `SortInfo`
    :raises AttributeError: If a sort with an invalid attr name is
        provided.
    :raises ValueError: If a sort not of type `SortInfo` is provided.
    :returns: A modified version of the provided query object.

    """
    # TODO - nested sorts
    if not isinstance(sorts, list):
        sorts = list(sorts)
    if len(query.column_descriptions) == 1:
        record_class = query.column_descriptions[0]["expr"]
        for sort in sorts:
            if not isinstance(sort, SortInfo):
                raise ValueError("The provided sort must be of type SortInfo.")
            attr_name = convert_key_names_func(sort.attr)
            if attr_name is not None and hasattr(record_class, attr_name):
                if sort.direction == "ASC":
                    query = query.order_by(
                        getattr(record_class, attr_name).asc())
                else:
                    query = query.order_by(
                        getattr(record_class, attr_name).desc())
            else:
                raise AttributeError("Invalid attribute.")
    return query


def apply_offset_and_limit(query, offset, limit):
    """Applies offset and limit to the query if appropriate.

    :param query: Any desired filters must already have been applied.
    :param offset: Integer used to offset the query result.
    :param limit: Integer used to limit the number of results returned.
    :returns: A modified query object with an offset and limit applied.

    """
    if offset is not None:
        offset = int(offset)
        query = query.offset(offset)
    if limit is not None:
        limit = int(limit)
        query = query.limit(limit)
    return query


def apply_load_options(query, model_class, embeds, strict=True, gettext=None):
    """Given a list of embed names, determine SQLAlchemy joinedloads.

    :param query: SQLAlchemy query object.
    :param model_class: SQLAlchemy model class being queried.
    :param embeds: List of embedded relationships.
    :param strict: Will ignore encountered errors if `False`.
    :param gettext: Optionally may be provided to translate error messages.
    :returns: An updated query object with load options applied to it.

    """
    if gettext is None:
        gettext = dummy_gettext
    _ = gettext
    options = []
    if not isinstance(embeds, list):
        embeds = [embeds]
    for item in embeds:
        split_names = item.split(".")
        parent_model = model_class
        sub_option = None
        for i, split_name in enumerate(split_names):
            if hasattr(parent_model, split_name):
                prop = getattr(parent_model, split_name)
                if isinstance(prop.property, RelationshipProperty):
                    child_model = inspect(prop).mapper.class_
                    if sub_option is None:
                        sub_option = joinedload(
                            getattr(parent_model, split_name))
                    else:
                        sub_option.joinedload(getattr(parent_model, split_name))
                    parent_model = child_model
            elif strict:
                raise AttributeError(_("Invalid attribute name: %{attrname}s",
                                       attrname=item))
        if sub_option is not None:
            options.append(sub_option)
    for option in options:
        query = query.options(option)
    return query
