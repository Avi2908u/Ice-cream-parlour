from django.shortcuts import render, redirect ,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Sale, IceCream, Vendor, User
from django.db.models import Sum, F, FloatField, ExpressionWrapper
from datetime import date
from django.contrib.auth import authenticate, login, get_user_model
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from .serializers import UserSerializer, IceCreamSerializer
from django.contrib import messages


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'owner':
            return Response({'detail': 'Not authorized'}, status=403)
        
        role = request.query_params.get('role')
        if role in ['vendor', 'customer']:
            users = User.objects.filter(role=role)
        else:
            users = User.objects.exclude(role='owner')

        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

class SummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'owner':
            return Response({'detail': 'Not authorized'}, status=403)

        total_units = Sale.objects.aggregate(Sum('units_sold'))['units_sold__sum'] or 0
        total_revenue = sum(sale.total_price for sale in Sale.objects.all())
        vendor_count = User.objects.filter(role='vendor').count()

        return Response({
            'units_sold': total_units,
            'total_revenue': total_revenue,
            'number_of_vendors': vendor_count
        })


User = get_user_model()

def signup_page(request):
    if request.method == 'POST':
        role = request.POST.get('signupUserType')
        name = request.POST.get('signupFullName')
        email = request.POST.get('signupEmail')
        username = request.POST.get('signupUsername')
        password = request.POST.get('signupPassword')
        confirm_password = request.POST.get('signupConfirmPassword')

        if not all([role, name, email, username, password, confirm_password]):
            return render(request, 'signup.html', {'error': 'Please fill all fields.'})
        
        if password != confirm_password:
            return render(request, 'signup.html', {'error': 'Passwords do not match.'})

        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {'error': 'Username already taken.'})
        
        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': 'Email already registered.'})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            first_name=name
        )
       
        if role == 'vendor':
           Vendor.objects.create(user=user, shop_name=f"{name}'s Shop")
        user.set_password(password)
        user.save()
        return redirect('/login/')  
    return render(request, 'signup.html')

def login_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_type = request.POST.get('user_type')

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            if user_type == 'owner':
                return redirect('owner')  
            elif user_type == 'vendor':
                if Vendor.objects.filter(user=user).exists():
                    return redirect('vendor')
                else:
                    return render(request, 'login.html', {'error': 'Vendor profile not found.'})
            elif user_type == 'customer':
                return redirect('customer')  
            else:
                return render(request, 'login.html', {'error': 'Invalid user type'})
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})

    return render(request, 'login.html')
@login_required
def owner_dashboard(request):
    vendors = Vendor.objects.all()

    # Vendor report list
    vendor_reports = []

    total_units_sold = 0
    total_revenue = 0

    for vendor in vendors:
        vendor_sales = Sale.objects.filter(product__vendor=vendor)
        units_sold = vendor_sales.aggregate(total=Sum('quantity_sold'))['total'] or 0

        revenue = vendor_sales.aggregate(
            total=Sum(ExpressionWrapper(
                F('quantity_sold') * F('product__price'),
                output_field=FloatField()
            ))
        )['total'] or 0

        vendor_reports.append({
            'shop_name': vendor.shop_name,
            'units_sold': units_sold,
            'revenue': revenue
        })

        total_units_sold += units_sold
        total_revenue += revenue

    context = {
        'total_revenue': total_revenue,
        'total_units_sold': total_units_sold,
        'active_vendors': vendors.count(),
        'vendor_reports': vendor_reports
    }

    return render(request, 'owner.html', context)   
@login_required
@api_view(['GET'])
def vendor_dashboard(request):
    vendor = Vendor.objects.get(user=request.user) 
    icecreams = IceCream.objects.filter(vendor=vendor)
    serializer = IceCreamSerializer(icecreams, many=True)
    today = date.today()
    sales_today = Sale.objects.filter(product__vendor=vendor, date_sold=today)
    total_stock = icecreams.aggregate(stock=Sum('stock'))['stock'] or 0
    total_items_sold_today = sales_today.aggregate(sold=Sum('quantity_sold'))['sold'] or 0
    total_revenue_today = sales_today.aggregate(
        revenue=Sum(ExpressionWrapper(F('quantity_sold') * F('product__price'), output_field=FloatField()))
    )['revenue'] or 0

    report = []
    for product in icecreams:
        sold_today = sales_today.filter(product=product).aggregate(sold=Sum('quantity_sold'))['sold'] or 0
        revenue = sold_today * float(product.price)
        report.append({
            'id': product.id,
            'flavour': product.flavour,
            'stock': product.stock,
            'sold_today': sold_today,
            'price': product.price,
            'revenue': revenue,
        })

    context = {
        'vendor': vendor,
        'total_stock': total_stock,
        'total_items_sold_today': total_items_sold_today,
        'total_revenue_today': total_revenue_today,
        'report': report,
    }
    return render(request, 'vendor.html', context)

@login_required
def customer_dashboard(request):
    vendors = Vendor.objects.prefetch_related('icecreams').all() 
    return render(request, 'customer_dashboard.html',{'venders':vendors})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(IceCream, id=product_id)
    cart = request.session.get('cart',{})
    if str(product_id) in cart:
        cart[str(product_id)] += 1
    else:
        cart[str(product_id)] = 1

    request.session['cart'] = cart
    return redirect('customer_dashboard')

@login_required
def view_cart(request):
    cart = request.session.get('cart', {})
    items = []
    total = 0

    for product_id, quantity in cart.items():
        product = get_object_or_404(IceCream, id=product_id)
        subtotal = product.price * quantity
        total += subtotal
        items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal})

    return render(request, 'cart.html', {'items': items, 'total': total})


@login_required
def buy_ice_cream(request):
    if request.method == 'POST':
        ice_cream_id = request.POST.get('ice_cream_id')
        quantity = int(request.POST.get('quantity', 1))

        ice_cream = get_object_or_404(IceCream, id=ice_cream_id)

        if ice_cream.stock < quantity:
            messages.error(request, f"Not enough stock available for {ice_cream.name}. Only {ice_cream.stock} left.")
            return redirect('/customer/')
        # Reduce stock
        ice_cream.stock -= quantity
        ice_cream.save()

        # Record the sale
        Sale.objects.create(
            product=ice_cream,
            customer=request.user,
            quantity_sold=quantity,
            date_sold=timezone.now().date()
        )
        messages.success(request, f"Successfully purchased {quantity} of {ice_cream.name}!")
        return redirect('customer')
        
    messages.error(request, "Invalid request method.")
    return redirect('customer')

@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('view_cart')

    for product_id, quantity in cart.items():
        product = get_object_or_404(IceCream, id=product_id)

        if product.stock < quantity:
            return render(request, 'cart.html', {
                'items': [],
                'total': 0,
                'error': f"Not enough stock for {product.name}."
            })

        product.stock -= quantity
        product.save()

        Sale.objects.create(
            product=product,
            quantity_sold=quantity,
            customer=request.user,
            date_sold=timezone.now().date()
        )

    request.session['cart'] = {}
    return render(request, 'checkout_success.html')