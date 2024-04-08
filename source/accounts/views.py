from django.contrib import messages
from django.contrib.auth import login, authenticate, REDIRECT_FIELD_NAME
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LogoutView as BaseLogoutView, PasswordChangeView as BasePasswordChangeView,
    PasswordResetDoneView as BasePasswordResetDoneView, PasswordResetConfirmView as BasePasswordResetConfirmView,
)
from django.views.generic.base import TemplateView
from django.shortcuts import get_object_or_404, redirect,render
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme as is_safe_url
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import View, FormView
from django.conf import settings
from django.http import  JsonResponse
# from django.core import serializers 
from datetime import timedelta, datetime
from django.db.models import Q, Sum
from django.utils import timezone
from operator import itemgetter

from .utils import (
    send_activation_email, send_reset_password_email, send_forgotten_username_email, send_activation_change_email,
)
from .forms import (
    SignInViaUsernameForm, SignInViaEmailForm, SignInViaEmailOrUsernameForm, SignUpForm,
    RestorePasswordForm, RestorePasswordViaEmailOrUsernameForm, RemindUsernameForm,
    ResendActivationCodeForm, ResendActivationCodeViaEmailForm, ChangeProfileForm, ChangeEmailForm, AddressForm,
    EquipmentForm, MaintenanceForm, ReceiptForm,
)
from .models import Activation, Address, Equipment, Maintenance, Receipt



class GuestOnlyView(View):
    def dispatch(self, request, *args, **kwargs):
        # Redirect to the index page if the user already authenticated
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)

        return super().dispatch(request, *args, **kwargs)


class LogInView(GuestOnlyView, FormView):
    template_name = 'accounts/log_in.html'

    @staticmethod
    def get_form_class(**kwargs):
        if settings.DISABLE_USERNAME or settings.LOGIN_VIA_EMAIL:
            return SignInViaEmailForm

        if settings.LOGIN_VIA_EMAIL_OR_USERNAME:
            return SignInViaEmailOrUsernameForm

        return SignInViaUsernameForm

    @method_decorator(sensitive_post_parameters('password'))
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        # Sets a test cookie to make sure the user has cookies enabled
        request.session.set_test_cookie()

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        request = self.request

        # If the test cookie worked, go ahead and delete it since its no longer needed
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()

        # The default Django's "remember me" lifetime is 2 weeks and can be changed by modifying
        # the SESSION_COOKIE_AGE settings' option.
        if settings.USE_REMEMBER_ME:
            if not form.cleaned_data['remember_me']:
                request.session.set_expiry(0)

        login(request, form.user_cache)

        redirect_to = request.POST.get(REDIRECT_FIELD_NAME, request.GET.get(REDIRECT_FIELD_NAME))
        url_is_safe = is_safe_url(redirect_to, allowed_hosts=request.get_host(), require_https=request.is_secure())

        if url_is_safe:
            return redirect(redirect_to)

        return redirect(settings.LOGIN_REDIRECT_URL)


class SignUpView(GuestOnlyView, FormView):
    template_name = 'accounts/sign_up.html'
    form_class = SignUpForm

    def form_valid(self, form):
        request = self.request
        user = form.save(commit=False)

        if settings.DISABLE_USERNAME:
            # Set a temporary username
            user.username = get_random_string()
        else:
            user.username = form.cleaned_data['username']

        if settings.ENABLE_USER_ACTIVATION:
            user.is_active = True

        # Create a user record
        user.save()

        # Change the username to the "user_ID" form
        if settings.DISABLE_USERNAME:
            user.username = f'user_{user.id}'
            user.save()

        if settings.ENABLE_USER_ACTIVATION:
            code = get_random_string(20)

            act = Activation()
            act.code = code
            act.user = user
            act.save()

            send_activation_email(request, user.email, code)

            messages.success(
                request, _('You are signed up. To activate the account, follow the link sent to the mail.'))
        else:
            raw_password = form.cleaned_data['password1']

            user = authenticate(username=user.username, password=raw_password)
            login(request, user)

            messages.success(request, _('You are successfully signed up!'))

        return redirect('accounts:log_in')


class ActivateView(View):
    @staticmethod
    def get(request, code):
        act = get_object_or_404(Activation, code=code)

        # Activate profile
        user = act.user
        user.is_active = True
        user.save()

        # Remove the activation record
        act.delete()

        messages.success(request, _('You have successfully activated your account!'))

        return redirect('accounts:log_in')


class ResendActivationCodeView(GuestOnlyView, FormView):
    template_name = 'accounts/resend_activation_code.html'

    @staticmethod
    def get_form_class(**kwargs):
        if settings.DISABLE_USERNAME:
            return ResendActivationCodeViaEmailForm

        return ResendActivationCodeForm

    def form_valid(self, form):
        user = form.user_cache

        activation = user.activation_set.first()
        activation.delete()

        code = get_random_string(20)

        act = Activation()
        act.code = code
        act.user = user
        act.save()

        send_activation_email(self.request, user.email, code)

        messages.success(self.request, _('A new activation code has been sent to your email address.'))

        return redirect('accounts:resend_activation_code')


class RestorePasswordView(GuestOnlyView, FormView):
    template_name = 'accounts/restore_password.html'

    @staticmethod
    def get_form_class(**kwargs):
        if settings.RESTORE_PASSWORD_VIA_EMAIL_OR_USERNAME:
            return RestorePasswordViaEmailOrUsernameForm

        return RestorePasswordForm

    def form_valid(self, form):
        user = form.user_cache
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        if isinstance(uid, bytes):
            uid = uid.decode()

        send_reset_password_email(self.request, user.email, token, uid)

        return redirect('accounts:restore_password_done')


class ChangeProfileView(LoginRequiredMixin, FormView):
    template_name = 'accounts/profile/change_profile.html'
    form_class = ChangeProfileForm

    def get_initial(self):
        user = self.request.user
        initial = super().get_initial()
        initial['first_name'] = user.first_name
        initial['last_name'] = user.last_name
        return initial

    def form_valid(self, form):
        user = self.request.user
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.save()

        messages.success(self.request, _('Profile data has been successfully updated.'))

        return redirect('accounts:change_profile')


class ChangeEmailView(LoginRequiredMixin, FormView):
    template_name = 'accounts/profile/change_email.html'
    form_class = ChangeEmailForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial['email'] = self.request.user.email
        return initial

    def form_valid(self, form):
        user = self.request.user
        email = form.cleaned_data['email']

        if settings.ENABLE_ACTIVATION_AFTER_EMAIL_CHANGE:
            code = get_random_string(20)

            act = Activation()
            act.code = code
            act.user = user
            act.email = email
            act.save()

            send_activation_change_email(self.request, email, code)

            messages.success(self.request, _('To complete the change of email address, click on the link sent to it.'))
        else:
            user.email = email
            user.save()

            messages.success(self.request, _('Email successfully changed.'))

        return redirect('accounts:change_email')


class ChangeEmailActivateView(View):
    @staticmethod
    def get(request, code):
        act = get_object_or_404(Activation, code=code)

        # Change the email
        user = act.user
        user.email = act.email
        user.save()

        # Remove the activation record
        act.delete()

        messages.success(request, _('You have successfully changed your email!'))

        return redirect('accounts:change_email')


class RemindUsernameView(GuestOnlyView, FormView):
    template_name = 'accounts/remind_username.html'
    form_class = RemindUsernameForm

    def form_valid(self, form):
        user = form.user_cache
        send_forgotten_username_email(user.email, user.username)

        messages.success(self.request, _('Your username has been successfully sent to your email.'))

        return redirect('accounts:remind_username')


class ChangePasswordView(BasePasswordChangeView):
    template_name = 'accounts/profile/change_password.html'

    def form_valid(self, form):
        # Change the password
        user = form.save()

        # Re-authentication
        login(self.request, user)

        messages.success(self.request, _('Your password was changed.'))

        return redirect('accounts:change_password')


class RestorePasswordConfirmView(BasePasswordResetConfirmView):
    template_name = 'accounts/restore_password_confirm.html'

    def form_valid(self, form):
        # Change the password
        form.save()

        messages.success(self.request, _('Your password has been set. You may go ahead and log in now.'))

        return redirect('accounts:log_in')


class RestorePasswordDoneView(BasePasswordResetDoneView):
    template_name = 'accounts/restore_password_done.html'


class LogOutConfirmView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/log_out_confirm.html'


class LogOutView(LoginRequiredMixin, BaseLogoutView):
    template_name = 'accounts/log_out.html'


############################# EVERYTHING BELOW IS ADDED FOR MY PROJECT #############################################



def address_form(request):
    addresses = Address.objects.filter(user=request.user)
    if request.method =='POST':
        form=AddressForm(request.POST)
        if form.is_valid():
            address_instance = form.save(commit=False)
            address_instance.user = request.user
            address_instance.save()
            messages.success(request, 'Address added successfully') 
            return redirect('accounts:address_form')
    else:
        form=AddressForm()

    return render(request, 'accounts/address_form.html', {'form':form, 'addresses':addresses})

 

def AddEquipment(request):
    addresses = Address.objects.filter(user=request.user)
    if request.method =='POST':
        form=EquipmentForm(request.POST)
        if form.is_valid():
            equipment_instance = form.save(commit=False)
            equipment_instance.user = request.user
            address_id = request.POST.get('address')
            equipment_instance.address_id = address_id
            existing_equipment = Equipment.objects.filter(
                address_id=address_id, component=equipment_instance.component, description=equipment_instance.description
            ).exists()

            if existing_equipment:
                messages.error(request, 'This equipment already exists for this address.')
            else:
                equipment_instance.save()
                messages.success(request, 'Equipment added successfully') 
            return redirect('accounts:add_equipment')
    else:
        form=EquipmentForm()
    return render(request, 'accounts/add_equipment.html', {'form':form, 'addresses':addresses})


def receipts(request):
    addresses = Address.objects.filter(user=request.user)
    if request.method == 'POST':
        form = ReceiptForm(request.POST, request.FILES)
        if form.is_valid():
            receipt_instance = form.save(commit=False)
            receipt_instance.user = request.user
            receipt_instance.save()
            messages.success(request, 'Receipt added successfully') 
            return redirect('accounts:receipts')
    else:
        form = ReceiptForm()
    
    return render(request, 'accounts/receipts.html', {'form': form, 'addresses': addresses})

def maintenance(request):
    user_addresses = Address.objects.filter(user=request.user)
    #components = Equipment.objects.filter(address__in=user_addresses)
    if request.method == 'POST':
        form = MaintenanceForm(request.POST, user=request.user) 
        if form.is_valid():
            maintenance_instance = form.save(commit=False)
            
            if maintenance_instance.maintenance_price < 0:
                messages.error(request, 'Cannot Enter a Negatice Price')

            else:
                maintenance_instance.save()
                messages.success(request, 'Maintenance record submitted successfully!') 
                return redirect('accounts:maintenance') 
    else:
        
        form = MaintenanceForm(user=request.user) 

    return render(request, 'accounts/maintenance.html', {'form': form,'user_addresses': user_addresses})


def equipment(request):
    equipment_instances = Equipment.objects.filter(address__user=request.user)
    
    equipment_list = []
    for equipment_instance in equipment_instances:
        address = equipment_instance.address.address
        user = equipment_instance.address.user
        description =equipment_instance.description
        maintenance_records = equipment_instance.maintenance_set.order_by('-dateCompleted')
        equipment_list.append({'equipment': equipment_instance, 'address': address, 'description':description, 'user': user,'maintenance_records': maintenance_records})
    return render(request, 'accounts/equipment.html', {'equipment_list': equipment_list})


def get_components(request):
    address_id = request.GET.get('address')
    components = Equipment.objects.filter(address_id=address_id).values('component')
    print(components)  # Print components for debugging
    return JsonResponse(list(components), safe=False)



def dashboard(request):
    user_addresses = Address.objects.filter(user=request.user)
    equipments = Equipment.objects.filter(address__user=request.user)
    now = datetime.now().date()



    total_properties = user_addresses.values('address').distinct().count()
    total_components = Equipment.objects.filter(address__user=request.user).count()
    # total_maintenance_tasks = Maintenance.objects.filter(component__address__user=request.user).count()
    total_overdue_tasks= 0
    # Initialize list to store component details
    component_next_maintenance = []

    
    for equipment in equipments:
        latest_maintenance = Maintenance.objects.filter(component=equipment).order_by('-dateCompleted').first()
        
        if latest_maintenance:
            # Calculate the next maintenance date based on the frequency
            next_maintenance_date = latest_maintenance.dateCompleted + timedelta(days=equipment.frequency * 30)  # Assuming frequency is in months
            
            current_date = datetime.now().date()
            if next_maintenance_date < current_date:
                total_overdue_tasks = total_overdue_tasks+1
                status = 'red'  # Overdue
            elif current_date <= next_maintenance_date < current_date + timedelta(days=30):
                status = 'yellow'  # Due within 30 days
            else:
                status = 'none'  # Not due yet
            # Check if the next maintenance is less than 2 months away from today
            if next_maintenance_date < now + timedelta(days=90):
                # Store the component and next maintenance date
                component_next_maintenance.append({
                    'component': equipment.component,
                    'description':equipment.description,
                    'address': equipment.address.address,
                    'next_maintenance_date': next_maintenance_date,
                    'status': status
                })


    return render(request, 'accounts/dashboard.html', {'component_next_maintenance': component_next_maintenance,
                                                        'total_overdue_tasks': total_overdue_tasks,
                                                        'total_properties': total_properties,
                                                        'total_components': total_components,
                                                        
                                                        })



def showReceipt(request):
    addresses = Address.objects.filter(user=request.user)
    components = Receipt.objects.filter(user=request.user).values_list('component', flat=True).distinct()
    
    address = request.GET.get('address')
    component = request.GET.get('component')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    low_price = request.GET.get('low_price')
    high_price = request.GET.get('high_price')

    # Construct a filter query based on user inputted parameters
    filter_query = {}
    if address:
        filter_query['address__address__icontains'] = address
    if component:
        filter_query['component__icontains'] = component
    if start_date:
        filter_query['date__gte'] = start_date
    if end_date:
        filter_query['date__lte'] = end_date
    if low_price:
        filter_query['price__gte'] = low_price
    if high_price:
        filter_query['price__lte'] = high_price

    
    receipts = Receipt.objects.filter(user=request.user, **filter_query)

    return render(request, 'accounts/show_receipt.html', {'receipts': receipts, 'addresses': addresses, 'components': components})


def delete(request, address_id):
    try:
        address = Address.objects.get(pk = address_id)
        address.delete()
        return redirect('accounts:address_form')
    except Address.DoesNotExist:
        return redirect('accounts:address_form')
    

def maintenance_delete(request, maintenance):
    try:
        maintenance = Maintenance.objects.get(pk = maintenance)
        maintenance.delete()
        return redirect('accounts:equipment')
    except Maintenance.DoesNotExist:
        return redirect('accounts:equipment')
    
def component_delete(request, component_id):
    try:
        component = Equipment.objects.get(pk = component_id)
        component.delete()
        return redirect('accounts:equipment')
    except Equipment.DoesNotExist:
        return redirect('accounts:equipment')

def receipt_delete(request, receipt_id):
    try:
        receipt = Receipt.objects.get(pk = receipt_id)
        receipt.delete()
        return redirect('accounts:show_receipt')
    except Receipt.DoesNotExist:
        return redirect('accounts:show_receipt')


def reports(request):
    addresses = Address.objects.filter(user=request.user)
    components = Equipment.objects.filter(address__user=request.user).values_list('component', flat=True).distinct()
    
    
    address = request.GET.get('address')
    component = request.GET.get('component')
    low_price = request.GET.get('low_price')
    high_price = request.GET.get('high_price')

    # Construct a filter query based on provided parameters
    filter_query = Q(component__address__user=request.user)
    if address:
        filter_query &= Q(component__address__address__icontains=address)
    if component:
        filter_query &= Q(component__component__icontains=component)
    if low_price:
        filter_query &= Q(maintenance_price__gte=low_price)
    if high_price:
        filter_query &= Q(maintenance_price__lte=high_price)
    
    # Fetch all maintenance records
    maintenance_records = Maintenance.objects.filter(filter_query)

    # Dictionary to store the latest maintenance record for each component at each address
    latest_maintenance_records = {}

    # Iterate over all maintenance records to find the latest one for each component at each address
    for record in maintenance_records:
        address = record.component.address
        component_name = record.component.component
        description = record.component.description
        last_maintenance_date = record.dateCompleted
        if (address, component_name) not in latest_maintenance_records:
            latest_maintenance_records[(address, component_name)] = {
                'record': record,
                'last_maintenance_date': last_maintenance_date
            }
        elif last_maintenance_date > latest_maintenance_records[(address, component_name)]['last_maintenance_date']:
            latest_maintenance_records[(address, component_name)] = {
                'record': record,
                'last_maintenance_date': last_maintenance_date
            }

    # Generate component_status_and_price list from latest maintenance records
    component_status_and_price = []
    for data in latest_maintenance_records.values():
        record = data['record']
        component = record.component
        description = record.component.description
        last_maintenance_date = data['last_maintenance_date']
        frequency = component.frequency
        if last_maintenance_date:
            next_due_date = last_maintenance_date + timedelta(days=30*frequency)
            status = "Current" if next_due_date >= timezone.now().date() else "Overdue"
        else:
            status = "No Maintenance"
        total_price = component.maintenance_set.filter(dateCompleted__lte=timezone.now().date()).aggregate(total=Sum('maintenance_price'))['total']
        component_status_and_price.append({'component': component, 'description':description,'status': status, 'next_due_date': next_due_date, 'total_price': total_price})

    component_status_and_price.sort(key=itemgetter('next_due_date'))
    return render(request, 'accounts/reports.html', {'component_status_and_price': component_status_and_price, 'addresses': addresses,  'components': components})

def getting_started(request):
    return render(request, 'accounts/getting_started.html')