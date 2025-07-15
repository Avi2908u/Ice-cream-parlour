

# Register your models here.
from django.contrib import admin
from .models import Product, CartItem, User, Vendor

admin.site.register(Product)
admin.site.register(CartItem)
admin.site.register(User)
admin.site.register(Vendor)