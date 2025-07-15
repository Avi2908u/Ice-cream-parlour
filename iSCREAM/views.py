
from .models import Product, CartItem
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from .models import Vendor, IceCreamProduct, Order, OrderItem, Sale, Customer
from .forms import VendorProductForm, VendorRegistrationForm
import json
from datetime import datetime, timedelta



def index(request):
    return render(request, 'login.html')

def owner_dashboard(request):
    return render(request, 'owner.html')
    

def customer_dashboard(request):
    return render(request, 'customer_dashboard.html')
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


@login_required
def vendor_dashboard(request):
    """Main vendor dashboard view"""
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        messages.error(request, "You don't have vendor access.")
        return redirect('home')
    
    # Get today's date
    today = timezone.now().date()
    
    # Calculate statistics
    total_products = vendor.products.count()
    total_stock = vendor.products.aggregate(total=Sum('stock_quantity'))['total'] or 0
    
    # Today's sales
    today_sales = Sale.objects.filter(
        vendor=vendor,
        created_at__date=today
    )
    
    items_sold_today = today_sales.aggregate(total=Sum('quantity'))['total'] or 0
    revenue_today = today_sales.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Get recent products with sales data
    products_with_sales = []
    for product in vendor.products.all()[:10]:  # Limit to recent 10 products
        today_product_sales = today_sales.filter(product=product)
        sold_today = today_product_sales.aggregate(total=Sum('quantity'))['total'] or 0
        product_revenue = today_product_sales.aggregate(total=Sum('total_amount'))['total'] or 0
        
        products_with_sales.append({
            'product': product,
            'sold_today': sold_today,
            'revenue_today': product_revenue
        })
    
    context = {
        'vendor': vendor,
        'total_products': total_products,
        'total_stock': total_stock,
        'items_sold_today': items_sold_today,
        'revenue_today': revenue_today,
        'products_with_sales': products_with_sales,
    }
    
    return render(request, '/dashboard/', context)

@login_required
def vendor_products(request):
    """Vendor products management"""
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        messages.error(request, "You don't have vendor access.")
        return redirect('home')
    
    products = vendor.products.all().order_by('-created_at')
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'vendor': vendor,
        'page_obj': page_obj,
    }
    
    return render(request, 'vendor/products.html', context)

@login_required
def add_product(request):
    """Add new ice cream product"""
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        messages.error(request, "You don't have vendor access.")
        return redirect('home')
    
    if request.method == 'POST':
        form = VendorProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.vendor = vendor
            product.save()
            messages.success(request, 'Product added successfully!')
            return redirect('vendor_products')
    else:
        form = VendorProductForm()
    
    context = {
        'form': form,
        'vendor': vendor,
    }
    
    return render(request, 'vendor/add_product.html', context)

@login_required
def edit_product(request, product_id):
    """Edit existing product"""
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        messages.error(request, "You don't have vendor access.")
        return redirect('home')
    
    product = get_object_or_404(IceCreamProduct, id=product_id, vendor=vendor)
    
    if request.method == 'POST':
        form = VendorProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('vendor_products')
    else:
        form = VendorProductForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
        'vendor': vendor,
    }
    
    return render(request, 'vendor/edit_product.html', context)

@login_required
def delete_product(request, product_id):
    """Delete product"""
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        messages.error(request, "You don't have vendor access.")
        return redirect('home')
    
    product = get_object_or_404(IceCreamProduct, id=product_id, vendor=vendor)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('vendor_products')
    
    context = {
        'product': product,
        'vendor': vendor,
    }
    
    return render(request, 'vendor/delete_product.html', context)

@login_required
def vendor_orders(request):
    """View vendor orders"""
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        messages.error(request, "You don't have vendor access.")
        return redirect('home')
    
    orders = Order.objects.filter(vendor=vendor).order_by('-created_at')
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'vendor': vendor,
        'page_obj': page_obj,
    }
    
    return render(request, 'vendor/orders.html', context)

@login_required
def update_order_status(request, order_id):
    """Update order status"""
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        return JsonResponse({'error': 'Vendor access required'}, status=403)
    
    order = get_object_or_404(Order, id=order_id, vendor=vendor)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            return JsonResponse({'success': True, 'new_status': new_status})
        else:
            return JsonResponse({'error': 'Invalid status'}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# API endpoints for real-time updates
@login_required
def api_vendor_stats(request):
    """API endpoint for real-time vendor statistics"""
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        return JsonResponse({'error': 'Vendor access required'}, status=403)
    
    today = timezone.now().date()
    
    # Calculate statistics
    total_products = vendor.products.count()
    total_stock = vendor.products.aggregate(total=Sum('stock_quantity'))['total'] or 0
    
    # Today's sales
    today_sales = Sale.objects.filter(
        vendor=vendor,
        created_at__date=today
    )
    
    items_sold_today = today_sales.aggregate(total=Sum('quantity'))['total'] or 0
    revenue_today = float(today_sales.aggregate(total=Sum('total_amount'))['total'] or 0)
    
    return JsonResponse({
        'total_products': total_products,
        'total_stock': total_stock,
        'items_sold_today': items_sold_today,
        'revenue_today': revenue_today,
    })

@login_required
def api_vendor_products(request):
    """API endpoint for vendor products with sales data"""
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        return JsonResponse({'error': 'Vendor access required'}, status=403)
    
    today = timezone.now().date()
    today_sales = Sale.objects.filter(
        vendor=vendor,
        created_at__date=today
    )
    
    products_data = []
    for product in vendor.products.all():
        today_product_sales = today_sales.filter(product=product)
        sold_today = today_product_sales.aggregate(total=Sum('quantity'))['total'] or 0
        product_revenue = float(today_product_sales.aggregate(total=Sum('total_amount'))['total'] or 0)
        
        products_data.append({
            'id': product.id,
            'name': product.name,
            'stock_left': product.stock_quantity,
            'sold_today': sold_today,
            'price': float(product.price),
            'revenue': product_revenue
        })
    
    return JsonResponse({'products': products_data})

# Customer views
def customer_products(request):
    """Display all available products to customers"""
    products = IceCreamProduct.objects.filter(
        is_available=True,
        stock_quantity__gt=0
    ).order_by('-created_at')
    
    # Filter by vendor if specified
    vendor_id = request.GET.get('vendor')
    if vendor_id:
        products = products.filter(vendor_id=vendor_id)
    
    # Filter by flavor if specified
    flavor = request.GET.get('flavor')
    if flavor:
        products = products.filter(flavor=flavor)
    
    vendors = Vendor.objects.filter(is_active=True)
    flavors = IceCreamProduct.FLAVOR_CHOICES
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'vendors': vendors,
        'flavors': flavors,
        'selected_vendor': vendor_id,
        'selected_flavor': flavor,
    }
    
    return render(request, 'customer/products.html', context)

@login_required
@csrf_exempt
def purchase_product(request):
    """Handle product purchase"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            
            # Get or create customer
            customer, created = Customer.objects.get_or_create(
                user=request.user,
                defaults={'phone': '', 'address': ''}
            )
            
            product = get_object_or_404(IceCreamProduct, id=product_id)
            
            # Check stock
            if product.stock_quantity < quantity:
                return JsonResponse({
                    'error': 'Insufficient stock',
                    'available_stock': product.stock_quantity
                }, status=400)
            
            # Create order and process purchase
            with transaction.atomic():
                # Create order
                order = Order.objects.create(
                    customer=customer,
                    vendor=product.vendor,
                    total_amount=product.price * quantity,
                    status='confirmed'
                )
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price
                )
                
                # Update stock
                product.stock_quantity -= quantity
                product.save()
                
                # Create sale record
                Sale.objects.create(
                    vendor=product.vendor,
                    product=product,
                    order=order,
                    quantity=quantity,
                    price=product.price,
                    total_amount=product.price * quantity
                )
            
            return JsonResponse({
                'success': True,
                'order_id': order.id,
                'message': 'Purchase successful!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def vendor_login(request):
    """Vendor login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Check if user is a vendor
            try:
                vendor = user.vendor
                login(request, user)
                return redirect('/vendor/dashboard/')
            except Vendor.DoesNotExist:
                messages.error(request, 'You do not have vendor access.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'vendor/login.html')

def vendor_logout(request):
    """Vendor logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('vendor_login')

def vendor_register(request):
    """Vendor registration view"""
    if request.method == 'POST':
        form = VendorRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vendor registration successful! Please login.')
            return redirect('vendor_login')
    else:
        form = VendorRegistrationForm()
    
    return render(request, 'vendor/register.html', {'form': form})