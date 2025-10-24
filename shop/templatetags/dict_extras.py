# yourapp/templatetags/dict_extras.py
from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Return dictionary.get(key) or empty string if not found."""
    if not dictionary:
        return ''
    return dictionary.get(key, '')
