from django.shortcuts import render, redirect ,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Sale, Product, CartItem, Vendor, User
from django.db.models import Sum, F, FloatField, ExpressionWrapper
from datetime import date
from django.contrib.auth import authenticate, login, logout
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSerializer, RegisterSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

     def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Account created successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=sta

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


def signup_page(request):
    if request.method == 'POST':
        role = request.POST.get('signupUserType')
        name = request.POST.get('signupFullName')
        email = request.POST.get('signupEmail')
        username = request.POST.get('signupUsername')
        password = request.POST.get('signupPassword')
        confirm_password = request.POST.get('signupConfirmPassword')
        print("1111",role)

        if not all([role, name, email, username, password, confirm_password]):
            return render(request, 'signup.html', {'error': 'Please fill all fields.'})
        
        if password != confirm_password:
            return render(request, 'signup.html', {'error': 'Passwords do not match.'})

        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {'error': 'Username already taken.'})
        
        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': 'Email already registered.'})

        user = User.objects.create(
            username=username,
            email=email,
            password=password,
            role=role,
            first_name=name
        )

        refresh = RefreshToken.for_user(user)
        return JsonResponse({
             "message": "User registered successfully!",
             "access": str(refresh.access_token),
             "refresh": str(refresh),
})


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
                return redirect('/owner/')  
            elif user_type == 'vendor':
                if Vendor.objects.filter(user=user).exists():
                    return redirect('/vendor/')
                else:
                    return render(request, 'login.html', {'error': 'Vendor profile not found.'})
            elif user_type == 'customer':
                return redirect('/customer/')  
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
def vendor_dashboard(request):
    vendor = Vendor.objects.get(user=request.user)

    # Get all vendor products
    products = Product.objects.filter(vendor=vendor)

    # Today's sales
    today = date.today()
    sales_today = Sale.objects.filter(product__vendor=vendor, date_sold=today)

    # Stats
    total_stock = products.aggregate(stock=Sum('stock'))['stock'] or 0
    total_items_sold_today = sales_today.aggregate(sold=Sum('quantity_sold'))['sold'] or 0
    total_revenue_today = sales_today.aggregate(
        revenue=Sum(ExpressionWrapper(F('quantity_sold') * F('product__price'), output_field=FloatField()))
    )['revenue'] or 0

    # Report
    report = []
    for product in products:
        sold_today = sales_today.filter(product=product).aggregate(sold=Sum('quantity_sold'))['sold'] or 0
        revenue = sold_today * float(product.price)
        report.append({
            'name': product.name,
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
    products = Product.objects.all()
    return render(request, 'customer_dashboard.html', {'products': products})
    
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    item, created = CartItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.quantity += 1
        item.save()
    return redirect('view_cart')

@login_required
def view_cart(request):
    items = CartItem.objects.filter(user=request.user)
    total = sum(item.product.price * item.quantity for item in items)
    return render(request, 'cart.html', {'items': items, 'total': total})

@login_required
def checkout(request):
    items = CartItem.objects.filter(user=request.user)
    total = sum(item.product.price * item.quantity for item in items)

    if request.method == 'POST':
        # Save each item as a Sale
        for item in items:
            Sale.objects.create(
                product=item.product,
                quantity_sold=item.quantity,
                vendor=item.product.vendor.user,
                units_sold=item.quantity,
                price_per_unit=item.product.price
            )
            item.product.stock -= item.quantity
            item.product.save()

        # Clear the cart
        items.delete()
        return render(request, 'checkout_success.html', {'total': total})

    return render(request, 'checkout.html', {'items': items, 'total': total})