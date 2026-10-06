"""Template helpers of the Framapétitions design system (DS-04)."""
import textwrap

from django import template
from django.forms import CheckboxInput, CheckboxSelectMultiple, RadioSelect, Select, SelectMultiple, Textarea
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

register = template.Library()


def _widget_class(widget):
    if isinstance(widget, CheckboxInput):
        return "fp-check-input"
    if isinstance(widget, (RadioSelect, CheckboxSelectMultiple)):
        return ""
    if isinstance(widget, (Select, SelectMultiple)):
        return "fp-select"
    if isinstance(widget, Textarea):
        return "fp-textarea"
    return "fp-input"


@register.filter
def fp_is_checkbox(field):
    return isinstance(field.field.widget, CheckboxInput)


@register.simple_tag
def fp_widget(field):
    """Render a bound field's widget with the design system class and its
    help and error ids in aria-describedby (see components/field.html)."""
    attrs = {}
    css = _widget_class(field.field.widget)
    existing = field.field.widget.attrs.get("class", "")
    if css:
        attrs["class"] = (existing + " " + css).strip()
    described = []
    if field.help_text:
        described.append(field.auto_id + "-help")
    if field.errors:
        described.append(field.auto_id + "-error")
        attrs["aria-invalid"] = "true"
    if described:
        attrs["aria-describedby"] = " ".join(described)
    return field.as_widget(attrs=attrs)


@register.filter
def fp_page_range(page):
    """Page numbers with ellipses: 1 … 4 5 6 … 20 (None stands for the ellipsis)"""
    return [None if number == page.paginator.ELLIPSIS else number
            for number in page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)]


class ExampleNode(template.Node):
    def __init__(self, nodelist, title):
        self.nodelist = nodelist
        self.title = title

    def render(self, context):
        html = textwrap.dedent(self.nodelist.render(context)).strip("\n")
        title = self.title.resolve(context)
        return format_html(
            '<div class="fp-example"><div class="fp-example-render">{}</div>'
            '<details class="fp-example-code"><summary>{}</summary><pre><code>{}</code></pre></details></div>',
            mark_safe(html), title, escape(html))


@register.tag
def fp_example(parser, token):
    """{% fp_example "Show the markup" %}...{% endfp_example %}: renders the
    markup, then shows it escaped (styleguide only)."""
    bits = token.split_contents()
    if len(bits) != 2:
        raise template.TemplateSyntaxError("fp_example takes one argument: the label of the markup toggle")
    nodelist = parser.parse(("endfp_example",))
    parser.delete_first_token()
    return ExampleNode(nodelist, parser.compile_filter(bits[1]))
