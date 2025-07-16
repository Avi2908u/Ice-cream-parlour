

# Register your models here.
from django.contrib import admin
from .models import IceCream, CartItem, User, Vendor

admin.site.register(IceCream)
admin.site.register(CartItem)
admin.site.register(User)
admin.site.register(Vendor)