from django import forms
from .models import IceCream, FlavorProposal

class IceCreamForm(forms.ModelForm):
    class Meta:
        model = IceCream
        fields = ['flavour', 'price', 'stock']

class FlavourProposalForm(forms.ModelForm):
    class Meta:
        model = FlavorProposal
        fields = ['name', 'description']


