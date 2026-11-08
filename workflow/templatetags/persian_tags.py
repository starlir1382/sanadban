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


@register.filter(name="jalali_datetime")
def jalali_datetime(value, fmt="%Y/%m/%d %H:%M"):
    """Converts a datetime to Jalali string format."""
    if not value:
        return ""
    try:
        import jdatetime
        from django.utils import timezone
        dt = value
        if hasattr(dt, "strftime"):
            if timezone.is_aware(dt):
                dt = timezone.localtime(dt)
            return jdatetime.datetime.fromgregorian(datetime=dt).strftime(fmt)
        return str(value)
    except Exception:
        return str(value)


@register.filter(name="jalali_datetime_full")
def jalali_datetime_full(value):
    """Converts a datetime to Jalali string format with seconds."""
    return jalali_datetime(value, fmt="%Y/%m/%d %H:%M:%S")


@register.filter(name="jalali_date")
def jalali_date(value):
    """Converts a date/datetime to Jalali date format."""
    return jalali_datetime(value, fmt="%Y/%m/%d")
