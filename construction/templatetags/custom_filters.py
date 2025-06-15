from django import template

register = template.Library()

@register.filter
def split_string(value, delimiter=','):
    """Разбивает строку по разделителю и возвращает список"""
    if not value:
        return []
    return str(value).split(delimiter)
