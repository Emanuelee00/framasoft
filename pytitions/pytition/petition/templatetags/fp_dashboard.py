"""Template helpers of the creator area (dashboard, wizard, petition settings)."""
import datetime

from django import template
from django.utils import timezone

register = template.Library()

# A petition is flagged in the lists when its deletion is this close
EXPIRY_WARNING_DAYS = 30


def _as_date(value):
    if isinstance(value, datetime.datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return None


@register.filter
def fp_days_left(value):
    """Days from today to a date or datetime (Petition.expires_at), None when there is no date."""
    day = _as_date(value)
    if day is None:
        return None
    return (day - timezone.localdate()).days


@register.filter
def fp_expires_soon(value):
    """True when the date is in EXPIRY_WARNING_DAYS days or less (today included)."""
    days = fp_days_left(value)
    return days is not None and days <= EXPIRY_WARNING_DAYS


@register.filter
def fp_no_autofocus(field):
    """Drop the autofocus a form sets on its first field, for forms that are not alone on the page."""
    field.field.widget.attrs.pop("autofocus", None)
    return field


@register.simple_tag
def fp_widget_described(field, describedby):
    """Like fp_ui.fp_widget, with an extra id in aria-describedby (explanation written by the template)."""
    from .fp_ui import _widget_class
    attrs = {}
    css = _widget_class(field.field.widget)
    if css:
        attrs["class"] = (field.field.widget.attrs.get("class", "") + " " + css).strip()
    described = [describedby]
    if field.help_text:
        described.append(field.auto_id + "-help")
    if field.errors:
        described.append(field.auto_id + "-error")
        attrs["aria-invalid"] = "true"
    attrs["aria-describedby"] = " ".join(described)
    return field.as_widget(attrs=attrs)
