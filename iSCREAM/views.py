from django.shortcuts import render, redirect ,get_object_or_404
from .models import Product, CartItem
from django.contrib.auth.decorators import login_required


def index(request):
    return render(request, 'login.html')

def owner_dashboard(request):
    return render(request, 'owner.html')
    
def vendor_dashboard(request):
    return render(request, 'vendor.html')

def customer_dashboard(request):
    return render(request, 'customer.html')
def product_list(request):
    products = Product.objects.all()
    return render(request, 'product_list.html', {'products': products})
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    item, created = CartItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.quantity += 1
        item.save()
    return redirect('cart:view_cart')

@login_required
def view_cart(request):
    items = CartItem.objects.filter(user=request.user)
    total = sum(item.product.price * item.quantity for item in items)
    return render(request, 'cart/view_cart.html', {'items': items, 'total': total})

@login_required
def checkout(request):
    items = CartItem.objects.filter(user=request.user)
    total = sum(item.product.price * item.quantity for item in items)

    if request.method == 'POST':
        # simulate order finalized
        items.delete()
        return render(request, 'cart/checkout_success.html', {'total': total})

    return render(request, 'cart/checkout.html', {'items': items, 'total': total})
