from django.contrib import admin
from .models import Activation, Address, Equipment, Maintenance

admin.site.register(Activation)
admin.site.register(Address)
admin.site.register(Equipment)
admin.site.register(Maintenance)
