from datetime import timedelta
from typing import Any, Mapping

from django import forms
from django.core.files.base import File
from django.db.models.base import Model
from django.forms import ValidationError
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms.utils import ErrorList
from django.utils import timezone
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from .models import Address, Equipment, Maintenance, Receipt


class UserCacheMixin:
    user_cache = None

class SignIn(UserCacheMixin, forms.Form):
    password = forms.CharField(label=_('Password'), strip=False, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if settings.USE_REMEMBER_ME:
            self.fields['remember_me'] = forms.BooleanField(label=_('Remember me'), required=False)

    def clean_password(self):
        password = self.cleaned_data['password']

        if not self.user_cache:
            return password

        if not self.user_cache.check_password(password):
            raise ValidationError(_('You entered an invalid password.'))

        return password


class SignInViaUsernameForm(SignIn):
    username = forms.CharField(label=_('Username'))

    @property
    def field_order(self):
        if settings.USE_REMEMBER_ME:
            return ['username', 'password', 'remember_me']
        return ['username', 'password']

    def clean_username(self):
        username = self.cleaned_data['username']

        user = User.objects.filter(username=username).first()
        if not user:
            raise ValidationError(_('You entered an invalid username.'))

        if not user.is_active:
            raise ValidationError(_('This account is not active.'))

        self.user_cache = user

        return username


class EmailForm(UserCacheMixin, forms.Form):
    email = forms.EmailField(label=_('Email'))

    def clean_email(self):
        email = self.cleaned_data['email']

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise ValidationError(_('You entered an invalid email address.'))

        if not user.is_active:
            raise ValidationError(_('This account is not active.'))

        self.user_cache = user

        return email


class SignInViaEmailForm(SignIn, EmailForm):
    @property
    def field_order(self):
        if settings.USE_REMEMBER_ME:
            return ['email', 'password', 'remember_me']
        return ['email', 'password']


class EmailOrUsernameForm(UserCacheMixin, forms.Form):
    email_or_username = forms.CharField(label=_('Email or Username'))

    def clean_email_or_username(self):
        email_or_username = self.cleaned_data['email_or_username']

        user = User.objects.filter(Q(username=email_or_username) | Q(email__iexact=email_or_username)).first()
        if not user:
            raise ValidationError(_('You entered an invalid email address or username.'))

        if not user.is_active:
            raise ValidationError(_('This account is not active.'))

        self.user_cache = user

        return email_or_username


class SignInViaEmailOrUsernameForm(SignIn, EmailOrUsernameForm):
    @property
    def field_order(self):
        if settings.USE_REMEMBER_ME:
            return ['email_or_username', 'password', 'remember_me']
        return ['email_or_username', 'password']


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = settings.SIGN_UP_FIELDS

    email = forms.EmailField(label=_('Email'), help_text=_('Required. Enter an existing email address.'))

    def clean_email(self):
        email = self.cleaned_data['email']

        user = User.objects.filter(email__iexact=email).exists()
        
        if user:
            raise ValidationError(_('You can not use this email address.'))

        return email


class ResendActivationCodeForm(UserCacheMixin, forms.Form):
    email_or_username = forms.CharField(label=_('Email or Username'))

    def clean_email_or_username(self):
        email_or_username = self.cleaned_data['email_or_username']

        user = User.objects.filter(Q(username=email_or_username) | Q(email__iexact=email_or_username)).first()
        if not user:
            raise ValidationError(_('You entered an invalid email address or username.'))

        if user.is_active:
            raise ValidationError(_('This account has already been activated.'))

        activation = user.activation_set.first()
        if not activation:
            raise ValidationError(_('Activation code not found.'))

        # now_with_shift = timezone.now() - timedelta(hours=24)
        # if activation.created_at > now_with_shift:
        #     raise ValidationError(_('Activation code has already been sent. You can request a new code.'))

        self.user_cache = user

        return email_or_username


class ResendActivationCodeViaEmailForm(UserCacheMixin, forms.Form):
    email = forms.EmailField(label=_('Email'))

    def clean_email(self):
        email = self.cleaned_data['email']

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise ValidationError(_('You entered an invalid email address.'))

        if user.is_active:
            raise ValidationError(_('This account has already been activated.'))

        activation = user.activation_set.first()
        if not activation:
            raise ValidationError(_('Activation code not found.'))

        now_with_shift = timezone.now() - timedelta(hours=24)
        if activation.created_at > now_with_shift:
            raise ValidationError(_('Activation code has already been sent. You can request a new code in 24 hours.'))

        self.user_cache = user

        return email


class RestorePasswordForm(EmailForm):
    pass


class RestorePasswordViaEmailOrUsernameForm(EmailOrUsernameForm):
    pass


class ChangeProfileForm(forms.Form):
    first_name = forms.CharField(label=_('First name'), max_length=30, required=False)
    last_name = forms.CharField(label=_('Last name'), max_length=150, required=False)


class ChangeEmailForm(forms.Form):
    email = forms.EmailField(label=_('Email'))

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email']

        if email == self.user.email:
            raise ValidationError(_('Please enter another email.'))

        user = User.objects.filter(Q(email__iexact=email) & ~Q(id=self.user.id)).exists()
        if user:
            raise ValidationError(_('You can not use this mail.'))

        return email


class RemindUsernameForm(EmailForm):
    pass


########################  THIS SECTIONS BEGINS MY ADDITION TO THIS PROJECT    ###################################


class AddressForm(forms.ModelForm):
    
    class Meta:
        model = Address
        fields = ['address']
    
    def clean_address(self):
        address = self.cleaned_data['address']

        if Address.objects.filter( address=address).exists():
            raise ValidationError(_('You cannot use this address as it already exists.'))

        return address

class EquipmentForm(forms.ModelForm):
    
    class Meta:
        model = Equipment
        fields = ['component', 'frequency']
    def clean_frequency(self):
        frequency = self.cleaned_data['frequency']
        if frequency <=0:
            raise forms.ValidationError("Frequency cannot be negative or zero.")
        return frequency


class MaintenanceForm(forms.ModelForm):
    dateCompleted = forms.DateField(widget=forms.SelectDateWidget)  

    class Meta:
        model = Maintenance
        fields = ['component', 'dateCompleted', 'maintenance_price', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),  # Set the number of rows as needed
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Retrieve user from kwargs
        super(MaintenanceForm, self).__init__(*args, **kwargs)
        if user:
            user_addresses = Address.objects.filter(user=user)
            self.fields['component'].queryset = Equipment.objects.filter(address__in=user_addresses)
        
        self.fields['component'].label_from_instance = lambda obj: f"{obj.address} - {obj.component}"

  
class ReceiptForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ['address', 'component', 'price', 'date', 'image']

    def __init__(self, *args, **kwargs):
        super(ReceiptForm, self).__init__(*args, **kwargs)
        self.fields['address'].required = True   

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price < 0:
            raise forms.ValidationError("Price must be a non-negative value.")
        return price
   
    def clean(self):
        cleaned_data = super().clean()
        address = cleaned_data.get('address')
        price = cleaned_data.get('price')
        
        if not address:
            raise forms.ValidationError("Please choose an address.")
        
        if price is not None and price < 0:
            raise forms.ValidationError("Price must be a non-negative value.")