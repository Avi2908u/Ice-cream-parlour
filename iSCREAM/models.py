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
    description = models.TextField(default="")
    image = models.ImageField(upload_to='proposed_flavors/', null=True, blank=True)

    def __str__(self):
        return f"{self.flavour} - {self.vendor.shop_name}"  # Fixed: was using self.name which doesn't exist

class FlavorProposal(models.Model):
    vendor = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # This should be the flavor name
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField()
    stock = models.PositiveIntegerField(default=0) 
    image = models.ImageField(upload_to='proposed_flavors/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.status}"
    
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart for {self.user.username}"
    
    def get_total_price(self):
        return sum(item.get_total_price() for item in self.cart_items.all())
    
    def get_total_items(self):
        return sum(item.quantity for item in self.cart_items.all())



class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(IceCream, on_delete=models.CASCADE, null=True, blank=True)
    proposal = models.ForeignKey(FlavorProposal, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)    
    class Meta:
        unique_together = [['cart', 'product'], ['cart', 'proposal']]
    
    def get_total_price(self):
        if self.product:
            return self.product.price * self.quantity
        elif self.proposal:
            return self.proposal.price * self.quantity
        return 0
    
    def get_item_name(self):
        if self.product:
            return self.product.flavour
        elif self.proposal:
            return self.proposal.name
        return "Unknown Item"
    
    def get_item_price(self):
        if self.product:
            return self.product.price
        elif self.proposal:
            return self.proposal.price
        return 0

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"
 
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
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(IceCream, on_delete=models.CASCADE, null=True, blank=True)
    proposal = models.ForeignKey(FlavorProposal, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    
    def get_total_price(self):
        return self.price * self.quantity