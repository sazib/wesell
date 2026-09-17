import datetime

from django import forms

from accounts.models import CustomUser
from shop.models import DeliveryArea


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"placeholder": "Full name"}))
    phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={"placeholder": "Phone number"}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"placeholder": "Email (optional)"}))
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Street / area / landmark"}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"placeholder": "City"}))
    grid_coords = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Optional map coordinates (latitude,longitude)",
    )
    delivery_area = forms.ModelChoiceField(queryset=DeliveryArea.objects.filter(is_active=True), required=False)
    delivery_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "min": str(datetime.date.today() + datetime.timedelta(days=1))})
    )
    delivery_time_slot = forms.ChoiceField(required=False, choices=[
        ("", "Any time"),
        ("10:00-12:00", "10:00 AM - 12:00 PM"),
        ("12:00-14:00", "12:00 PM - 2:00 PM"),
        ("14:00-16:00", "2:00 PM - 4:00 PM"),
        ("16:00-18:00", "4:00 PM - 6:00 PM"),
        ("18:00-20:00", "6:00 PM - 8:00 PM"),
    ])
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Special instructions (optional)"}))

    def clean_delivery_date(self):
        date = self.cleaned_data.get("delivery_date")
        if date and date < datetime.date.today() + datetime.timedelta(days=1):
            raise forms.ValidationError("Delivery date must be at least one day in the future.")
        return date


class ShippingAddressForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Full name"}),
    )
    phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={"placeholder": "Phone number"}))
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Street / area / landmark"}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"placeholder": "City"}))

    class Meta:
        model = CustomUser
        fields = ("full_name", "phone", "address", "city")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and not self.initial.get("full_name"):
            self.initial["full_name"] = self.instance.get_full_name()

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data.get("full_name", "").strip()
        if full_name:
            parts = full_name.split(" ", 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else user.last_name
        if commit:
            user.save()
        return user


class CustomCakeForm(forms.Form):
    occasion = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"placeholder": "e.g. Birthday, Anniversary"}))
    theme = forms.CharField(required=False, max_length=200, widget=forms.TextInput(attrs={"placeholder": "Theme / design idea"}))
    size = forms.ChoiceField(choices=[
        ("", "Select size"),
        ("half_kg", "Half Kg (serves 5-8)"),
        ("one_kg", "1 Kg (serves 10-14)"),
        ("two_kg", "2 Kg (serves 20-28)"),
        ("small", "6 inch"),
        ("medium", "8 inch"),
        ("large", "10 inch"),
    ])
    flavor = forms.ChoiceField(choices=[
        ("", "Select flavor"),
        ("vanilla", "Vanilla"),
        ("chocolate", "Chocolate"),
        ("red_velvet", "Red Velvet"),
        ("strawberry", "Strawberry"),
        ("butterscotch", "Butterscotch"),
        ("pineapple", "Pineapple"),
        ("mango", "Mango"),
        ("eggless_chocolate", "Eggless Chocolate"),
        ("eggless_vanilla", "Eggless Vanilla"),
    ])
    filling = forms.ChoiceField(required=False, choices=[
        ("", "None"),
        ("cream", "Fresh Cream"),
        ("chocolate_ganache", "Chocolate Ganache"),
        ("fruit", "Fruit Filling"),
        ("cheese", "Cream Cheese"),
        ("jam", "Jam"),
    ])
    base_price = forms.DecimalField(required=False, max_digits=10, decimal_places=2, widget=forms.HiddenInput())
    quantity = forms.IntegerField(min_value=1, max_value=20, initial=1, widget=forms.HiddenInput())
    reference_photo = forms.ImageField(required=False, help_text="Upload a reference photo for your custom design")
    notes = forms.CharField(required=False, max_length=500, widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Anything else we should know about your cake?"}))