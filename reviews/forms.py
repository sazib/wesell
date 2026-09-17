from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "title", "comment")
        widgets = {
            "rating": forms.HiddenInput(),
            "title": forms.TextInput(attrs={"placeholder": "Short title (optional)"}),
            "comment": forms.Textarea(attrs={"rows": 4, "placeholder": "Share your experience with the product..."}),
        }