from django.shortcuts import render, redirect ,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import IceCream, CartItem, Vendor, User, FlavorProposal,Cart, Sale, OrderItem, Order
from .forms import IceCreamForm
from django.db.models import Sum, F, FloatField, ExpressionWrapper
from datetime import date
from django.contrib.auth import authenticate, login, get_user_model, logout
from rest_framework import generics ,viewsets, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, action
from .serializers import UserSerializer, VendorIceCreamSerializer, IceCreamSerializer, FlavorProposalSerializer
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from django.http import JsonResponse


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
            first_name=name
        )
       
        if role == 'vendor':
           Vendor.objects.create(user=user, shop_name=f"{name}'s Shop")
        user.save()


        if user:
            login(request, user)
            if role == 'vendor':
                if Vendor.objects.filter(user=user).exists():
                    return redirect('/vendor/')
            elif role == 'customer':
                return redirect('/customer/')  
        else:
            return render(request, 'signup.html', {'error': 'Invalid credentials'})
         
    return render(request, 'signup.html')

@csrf_protect
@csrf_exempt
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


def logout_view(request):
    logout(request)
    return redirect('/login/')

def approve_proposal(request, proposal_id):
    proposal = get_object_or_404(FlavorProposal, id=proposal_id)
    
    vendor = get_object_or_404(Vendor, user=proposal.vendor)
    if proposal.status == 'pending':
      IceCream.objects.create(
        vendor=vendor,
        flavour=proposal.name,
        price=proposal.price,
        description=proposal.description,
        stock=proposal.stock,  
        image=proposal.image 
      )
    
      proposal.status = 'approved'
      proposal.save()
      
    proposal.status = 'approved'
    proposal.save()
    
    messages.success(request, f"Proposal '{proposal.name}' has been approved and added to the catalog!")
    return redirect('/owner/')


def reject_proposal(request, proposal_id):
    if request.user.role != 'owner':
        messages.error(request, "Not authorized to reject proposals")
        return redirect('owner')
    
    proposal = get_object_or_404(FlavorProposal, id=proposal_id)
    
    # Delete the proposal from database
    proposal_name = proposal.name
    proposal.delete()
    
    messages.success(request, f"Proposal '{proposal_name}' has been rejected and removed!")
    return redirect('/owner/')

@login_required
def owner_dashboard(request):
    today = date.today()
    vendors = Vendor.objects.prefetch_related('icecreams').all()
    proposals = FlavorProposal.objects.filter(status='pending')
    approved_stock = FlavorProposal.objects.filter(status='approved').aggregate(
    total=Sum('stock'))['total'] or 0
    total_items_sold = 0
    total_revenue = 0
    total_stock_items = 0

    vendor_data = []

    for vendor in vendors:
        icecreams = vendor.icecreams.all()
        stock_items = icecreams.aggregate(total=Sum('stock'))['total'] or 0

        sales_today = Sale.objects.filter(
            product__in=icecreams,
            date_sold=today
        )

        items_sold_today = sales_today.aggregate(sold=Sum('quantity_sold'))['sold'] or 0

        revenue_today = sales_today.aggregate(
            revenue=Sum(ExpressionWrapper(F('quantity_sold') * F('product__price'), output_field=FloatField()))
        )['revenue'] or 0

        vendor_data.append({
            'shop_name': vendor.shop_name,
            'vendor_id': vendor.id,
            'joined_date': vendor.user.date_joined.strftime('%b %Y'),
            'revenue_today': revenue_today,
            'stock_items': stock_items,
            'sold_today': items_sold_today,
        })

        total_items_sold += items_sold_today
        total_revenue += revenue_today
        total_stock_items += stock_items

    context = {
        'vendor_data': vendor_data,
        'total_vendors': vendors.count(),
        'total_revenue': total_revenue,
        'total_items_sold': total_items_sold,
        'total_stock_items': total_stock_items,
        'pending_proposals': proposals, 
        'total_stock': approved_stock,

    }

    return render(request, "owner.html", context)

@login_required
def vendor_dashboard(request):
    vendor = Vendor.objects.get(user=request.user) 
    icecreams = IceCream.objects.filter(vendor=vendor)
    vendor_proposals = FlavorProposal.objects.filter(vendor=request.user)
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
            'name': product.flavour,
            'stock': product.stock,
            'sold_today': sold_today,
            'price': product.price,
            'revenue': revenue,
        })
    proposal_report = []
    for proposal in vendor_proposals:
      proposal_report.append({
        'name': proposal.name,
        'stock': proposal.stock,
        'price': proposal.price,
        'description': proposal.description,
        'status': proposal.status,
        'applied_date': proposal.created_at,
    })
    context = {
        'vendor': vendor,
        'total_stock': total_stock,
        'total_items_sold_today': total_items_sold_today,
        'total_revenue_today': total_revenue_today,
        'report': report,
        'proposals': proposal_report, 

    }
    return render(request, 'vendor.html', context)

@login_required
def get_cart_count(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    total_items = sum(item.quantity for item in cart.cart_items.all())
    return JsonResponse({'count': total_items})

@login_required
def customer_dashboard(request):
    vendors = Vendor.objects.prefetch_related('icecreams').all() 
    accepted_proposals = FlavorProposal.objects.filter(status='approved').select_related('vendor')
    
    cart = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.cart_items.all()
    cart_total = cart.get_total_price()
        
    context = {
            'vendors': vendors,
            'accepted_proposals': accepted_proposals,
            'cart_items': cart_items,
            'cart_total': cart_total,
        }
        
    return render(request, 'customer_dashboard.html', context)
    
def logout_view(request):
    logout(request)
    return redirect('/login/') 

@login_required
def add_to_cart(request, product_id):
   if request.method == 'POST':
        try:
            icecream = get_object_or_404(IceCream, id=product_id)
            
            # Check stock
            if icecream.stock <= 0:
                messages.error(request, f"{icecream.flavour} is out of stock!")
                return redirect('customer_dashboard')
            
            # Get or create cart
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            # Get or create cart item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=icecream,
                defaults={'quantity': 1}
            )
            
            if not created:
                # Check if we can add more
                if cart_item.quantity >= icecream.stock:
                    messages.error(request, f"Cannot add more {icecream.flavour}. Stock limit reached!")
                    return redirect('customer_dashboard')
                
                cart_item.quantity += 1
                cart_item.save()
                messages.success(request, f"Added another {icecream.flavour} to cart!")
            else:
                messages.success(request, f"Added {icecream.flavour} to cart!")
            
        except Exception as e:
            messages.error(request, f"Error adding to cart: {str(e)}")
   return redirect('customer_dashboard')

@login_required
def add_proposal_to_cart(request, proposal_id):
    """Add approved proposal to cart"""
    if request.method == 'POST':
        try:
            proposal = get_object_or_404(FlavorProposal, id=proposal_id, status='accepted')
            
            # Check stock
            if proposal.stock <= 0:
                messages.error(request, f"{proposal.name} is out of stock!")
                return redirect('customer_dashboard')
            
            # Get or create cart
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            # Get or create cart item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                proposal=proposal,
                defaults={'quantity': 1}
            )
            
            if not created:
                # Check if we can add more
                if cart_item.quantity >= proposal.stock:
                    messages.error(request, f"Cannot add more {proposal.name}. Stock limit reached!")
                    return redirect('customer_dashboard')
                
                cart_item.quantity += 1
                cart_item.save()
                messages.success(request, f"Added another {proposal.name} to cart!")
            else:
                messages.success(request, f"Added {proposal.name} to cart!")
            
        except Exception as e:
            messages.error(request, f"Error adding to cart: {str(e)}")
    
    return redirect('customer_dashboard')


@login_required
@require_POST
def update_cart_quantity(request):
    """Update cart item quantity"""
    product_id = request.POST.get('product_id')
    action = request.POST.get('action')
    cart = get_object_or_404(Cart, user=request.user)

    cart_item = None
    max_stock = 0
    item_name = ''

    try:
        # Try to find cart item as a regular product
        cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
        max_stock = cart_item.product.stock
        item_name = cart_item.product.flavour
    except CartItem.DoesNotExist:
        try:
            # Try as a proposal item
            cart_item = CartItem.objects.get(cart=cart, proposal_id=product_id)
            max_stock = cart_item.proposal.stock
            item_name = cart_item.proposal.name
        except CartItem.DoesNotExist:
            messages.error(request, "Item not found in cart!")
            return redirect('customer_dashboard')

    if action == 'increase':
        if cart_item.quantity < max_stock:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f"Increased {item_name} quantity!")
        else:
            messages.error(request, f"Cannot add more {item_name}. Stock limit reached!")

    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
            messages.success(request, f"Decreased {item_name} quantity!")
        else:
            cart_item.delete()
            messages.success(request, f"Removed {item_name} from cart!")

    return redirect('customer_dashboard')

def remove_from_cart(request):
    if request.method == 'POST':
        try:
            product_id = request.POST.get('product_id')
            cart = get_object_or_404(Cart, user=request.user)
            
            # Find and remove cart item
            cart_item = None
            try:
                cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
                item_name = cart_item.product.flavour
            except CartItem.DoesNotExist:
                try:
                    cart_item = CartItem.objects.get(cart=cart, proposal_id=product_id)
                    item_name = cart_item.proposal.name
                except CartItem.DoesNotExist:
                    messages.error(request, "Item not found in cart!")
                    return redirect('customer_dashboard')
            
            cart_item.delete()
            messages.success(request, f"Removed {item_name} from cart!")
            
        except Exception as e:
            messages.error(request, f"Error removing from cart: {str(e)}")
    
    return redirect('customer_dashboard')


def cart_view(request):
    try:
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.cart_items.all()
        
        items_data = []
        for item in cart_items:
            items_data.append({
                'id': item.product.id if item.product else item.proposal.id,
                'name': item.get_item_(),
                'price': float(item.get_item_price()),
                'quantity': item.quantity,
                'total': float(item.get_total_price()),
                'is_proposal': bool(item.proposal)
            })
        
        return JsonResponse({
            'items': items_data,
            'total': float(cart.get_total_price()),
            'count': cart.get_total_items()
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def checkout(request):
    try:
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.cart_items.all()
        
        if not cart_items:
            messages.error(request, "Your cart is empty!")
            return redirect('customer_dashboard')
        
        # Check stock availability
        for item in cart_items:
            if item.product:
                if item.quantity > item.product.stock:
                    messages.error(request, f"Not enough stock for {item.product.flavour}!")
                    return redirect('customer_dashboard')
            elif item.proposal:
                if item.quantity > item.proposal.stock:
                    messages.error(request, f"Not enough stock for {item.proposal.name}!")
                    return redirect('customer_dashboard')
        
        total_amount = cart.get_total_price()
        
        # Create order with transaction
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                total_amount=total_amount,
                status='completed'
            )
            
            # Create order items and update stock
            for item in cart_items:
                if item.product:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price
                    )
                    # Update stock
                    item.product.stock -= item.quantity
                    item.product.save()

                    Sale.objects.create(
                        product=item.product,
                        quantity_sold=item.quantity,
                        vendor=item.product.vendor.user,
                        customer=request.user,
                        units_sold=item.quantity,
                        price_per_unit=item.product.price,
                    )
                
                elif item.proposal:
                    OrderItem.objects.create(
                        order=order,
                        proposal=item.proposal,
                        quantity=item.quantity,
                        price=item.proposal.price
                    )
                    # Update stock
                    item.proposal.stock -= item.quantity
                    item.proposal.save()
            
            # Clear cart
            cart_items.delete()
            
            messages.success(request, f"🎉 Purchase Successful! Order #{order.id} has been placed. Total: ${total_amount}")
            
    except Exception as e:
        messages.error(request, f"Checkout error: {str(e)}")
    
    return redirect('customer_dashboard')

@login_required
def add_flavour(request):
    vendor = get_object_or_404(Vendor, user=request.user)

    if request.method == 'POST':
        form = IceCreamForm(request.POST)
        if form.is_valid():
            ice_cream = form.save(commit=False)
            ice_cream.vendor = vendor  
            ice_cream.save()
            return redirect('vendor_dashboard')
    else:
        form = IceCreamForm()

    return render(request, 'add_flavour.html', {'form': form})

def submit_flavour_proposal(request):
    if request.method == 'POST':
        vendor = request.user
        name = request.POST.get('flavor_name')
        description = request.POST.get('description')
        price = request.POST.get('base_price')
        image = request.FILES.get('image')  
        stock = request.POST.get('stock')  

        if not name or not description:
            messages.error(request, "Please fill out both fields.")
            return redirect('/vendor/')

        FlavorProposal.objects.create(
            vendor=vendor,
            name=name,
            price=price,
            description=description,
            status='pending',
            image=image,
            stock=stock
        )

        messages.success(request, "Proposal submitted successfully!")
        return redirect('/vendor/')
    
    return redirect('/vendor/')