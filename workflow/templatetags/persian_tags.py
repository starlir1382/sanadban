from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_FA_DIGITS_TRANS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


@register.filter(name="fa_digits")
def fa_digits(value):
    """Converts 0-9 to Persian ۰-۹."""
    if value is None:
        return ""
    return str(value).translate(_FA_DIGITS_TRANS)


@register.filter(name="persian_digits")
def persian_digits(value):
    """Alias for fa_digits."""
    return fa_digits(value)


@register.filter(name="fa_number")
def fa_number(value):
    """Formats a number with thousands separators in Persian digits (e.g. 1,234,567 -> ۱,۲۳۴,۵۶۷)."""
    if value is None or value == "":
        return ""
    try:
        if isinstance(value, float):
            formatted = f"{value:,.2f}".rstrip("0").rstrip(".")
        else:
            val_int = int(value)
            formatted = f"{val_int:,}"
        return formatted.translate(_FA_DIGITS_TRANS)
    except (ValueError, TypeError):
        return fa_digits(value)


@register.filter(name="fa_currency")
def fa_currency(value):
    """Formats amount with thousands separators and 'ریال' suffix."""
    if value is None or value == "" or value == 0:
        return "-"
    formatted = fa_number(value)
    return mark_safe(f"{formatted} <span class='unit'>ریال</span>")
