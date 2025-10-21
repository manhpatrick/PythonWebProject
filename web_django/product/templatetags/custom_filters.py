from django import template

register = template.Library()

@register.filter(name='split')
def split(value, arg):
    """
    Split string by delimiter
    Usage: {{ email|split:"@"|first }}
    """
    if not value:
        return []
    return value.split(arg)
