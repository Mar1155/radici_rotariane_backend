from django import template

register = template.Library()


@register.filter
def get_attr(obj, name):
    """
    Safe attribute/dict lookup for templates.
    Returns None when the attribute/key is missing instead of triggering noisy
    variable-resolution debug traces.
    """
    if obj is None:
        return None

    if isinstance(obj, dict):
        return obj.get(name)

    return getattr(obj, name, None)
