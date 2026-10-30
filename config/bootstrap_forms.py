from django import forms


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css = widget.attrs.get('class', '')
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs['class'] = f'{css} form-select'.strip()
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = f'{css} form-check-input'.strip()
            else:
                widget.attrs['class'] = f'{css} form-control'.strip()
            widget.attrs.setdefault('placeholder', str(field.label or ''))
