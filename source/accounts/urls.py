from django.urls import path


from .views import (
    LogInView, ResendActivationCodeView, RemindUsernameView, SignUpView, ActivateView, LogOutView,
    ChangeEmailView, ChangeEmailActivateView, ChangeProfileView, ChangePasswordView,
    RestorePasswordView, RestorePasswordDoneView, RestorePasswordConfirmView, LogOutConfirmView,address_form, AddEquipment, 
    maintenance,equipment, get_components, receipts, index
)

app_name = 'accounts'

urlpatterns = [
    path('log-in/', LogInView.as_view(), name='log_in'),
    path('log-out/confirm/', LogOutConfirmView.as_view(), name='log_out_confirm'),
    path('log-out/', LogOutView.as_view(), name='log_out'),

    path('resend/activation-code/', ResendActivationCodeView.as_view(), name='resend_activation_code'),

    path('sign-up/', SignUpView.as_view(), name='sign_up'),
    path('activate/<code>/', ActivateView.as_view(), name='activate'),

    path('restore/password/', RestorePasswordView.as_view(), name='restore_password'),
    path('restore/password/done/', RestorePasswordDoneView.as_view(), name='restore_password_done'),
    path('restore/<uidb64>/<token>/', RestorePasswordConfirmView.as_view(), name='restore_password_confirm'),

    path('remind/username/', RemindUsernameView.as_view(), name='remind_username'),

    path('change/profile/', ChangeProfileView.as_view(), name='change_profile'),
    path('change/password/', ChangePasswordView.as_view(), name='change_password'),
    path('change/email/', ChangeEmailView.as_view(), name='change_email'),
    path('change/email/<code>/', ChangeEmailActivateView.as_view(), name='change_email_activation'),
    path('address/form/', address_form, name='address_form'),
    path('add/equipment/', AddEquipment, name= 'add_equipment'),
    path('receipts/', receipts, name='receipts'),
    path('maintenance/', maintenance, name = 'maintenance'),
    path('equipment/', equipment, name = 'equipment'),
    path('get-components/', get_components, name='get_components'),
    path('', index, name= 'index'),
    
]
