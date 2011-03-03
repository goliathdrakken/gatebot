from django import forms

from pygate.core import models

ALL_TAPS = models.Gate.objects.all()

class GeneralSettingsForm(forms.Form):
  name = forms.CharField(help_text='Name of this Kegbot system')

class ChangeKegForm(forms.Form):
  description = forms.CharField(required=False,
      help_text='Public description of this specific keg (optional)')

class TapForm(forms.ModelForm):
  class Meta:
    model = models.Gate

#BeerTypeFormSet = inlineformset_factory(models.Brewer, models.BeerType)
