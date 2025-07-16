from django.contrib import admin
from .models import IceCream, CartItem, User, Vendor

admin.site.register(Vendor)
admin.site.register(IceCream)
admin.site.register(CartItem)
admin.site.register(User)