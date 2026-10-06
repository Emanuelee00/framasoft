# -*- coding: utf-8 -*-
"""Widgets for Pytition

It defines representations for HTML input elements.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/ref/forms/widgets/
"""

import json

from colorfield.widgets import ColorWidget as BaseColorWidget
from django import forms

class SwitchWidget(forms.CheckboxInput):
    template_name = "petition/widgets/SwitchInput.html"

    def get_context(self, name, value, attrs):
        if attrs == None:
            attrs = {}
        if 'class' in attrs:
            attrs['class'] = attrs['class'] + " custom-control-input"
        else:
            attrs.update({'class': 'custom-control-input'})

        ctx = super(SwitchWidget, self).get_context(name, value, attrs)
        ctx['widget'].update({'label': self.label})
        return ctx

    def __init__(self, *args, **kwargs):
        super(SwitchWidget, self).__init__(*args, **kwargs)
        if 'label' in kwargs:
            self.label = kwargs.pop('label')

class SwitchField(forms.BooleanField):
    widget = SwitchWidget

    def __init__(self, *args, **kwargs):
        super(SwitchField, self).__init__(*args, **kwargs)
        if 'label' in kwargs:
            self.widget.label = kwargs['label']

    def get_bound_field(self, form, field_name):
        bf = super(SwitchField, self).get_bound_field(form, field_name)
        bf.label_tag = self.label_tag
        return bf

    def label_tag(self, contents=None, attrs=None, label_suffix=None):
        return ""

# framapetitions: S13 - django-colorfield writes the jscolor options in a loose JS syntax that
# jscolor evaluates with new Function(), which the Content-Security-Policy blocks.
# Same widget, with the options as strict JSON (parsed with JSON.parse).
class ColorWidget(BaseColorWidget):
    template_name = "petition/widgets/color.html"

    def get_context(self, name, value, attrs=None):
        context = super().get_context(name, value, attrs)
        options = {"hash": True, "width": 225, "height": 150, "format": context["format"],
                   "required": bool(context.get("required")), "paletteCols": 4, "paletteHeight": 28}
        if context.get("palette"):
            options["palette"] = list(context["palette"])
        context["jscolor_options"] = json.dumps(options)
        return context
