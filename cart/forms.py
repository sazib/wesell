from django import forms

from .models import Product


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)
    size = forms.ChoiceField(choices=[], required=False)
    flavor = forms.ChoiceField(choices=[], required=False)

    def __init__(self, *args, product: Product | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        if product:
            size_labels = dict(Product.Size.choices)
            self.fields["size"].choices = [
                (s, size_labels.get(s, s.title())) for s in (product.sizes or [])
            ]
            self.fields["flavor"].choices = [(f, f.title()) for f in (product.flavors or [])]
            if len(self.fields["size"].choices) == 1:
                self.fields["size"].initial = self.fields["size"].choices[0][0]
            if len(self.fields["flavor"].choices) == 1:
                self.fields["flavor"].initial = self.fields["flavor"].choices[0][0]


class UpdateCartItemForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=99)