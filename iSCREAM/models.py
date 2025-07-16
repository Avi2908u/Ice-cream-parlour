from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('vendor', 'Vendor'),
        ('customer', 'Customer'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')

class Vendor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    shop_name = models.CharField(max_length=100, default='Unnamed Vendor')

    def __str__(self):
        return self.shop_name
    
class IceCream(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="icecreams")
    flavour = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)  

    def __str__(self):
        return f"{self.name} ({self.flavour})"

class FlavorProposal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    vendor = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.flavor_name} - {self.status}"


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey('IceCream', on_delete=models.CASCADE)  # Fix here
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"


class Sale(models.Model):

    product = models.ForeignKey(IceCream, on_delete=models.CASCADE)
    quantity_sold = models.PositiveIntegerField()
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vendor_sales', null=True, blank=True)
    date_sold = models.DateField(default=timezone.now)
    units_sold = models.PositiveIntegerField()
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    @property
    def total_price(self):
        return self.units_sold * self.price_per_unit

    def revenue(self):
        return self.quantity_sold * self.product.price
    




