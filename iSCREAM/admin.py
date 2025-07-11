

# Register your models here.
from django.contrib import admin
from .models import Product, CartItem

admin.site.register(Product)
admin.site.register(CartItem)
