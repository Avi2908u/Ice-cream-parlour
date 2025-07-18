from django.shortcuts import render, redirect ,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Sale, IceCream, CartItem, Vendor, User, FlavorProposal
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
            role=role,
            first_name=name
        )
       
        if role == 'vendor':
           Vendor.objects.create(user=user, shop_name=f"{name}'s Shop")
        user.set_password(password)
        user.save()
        return redirect('login')  
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


def get_cart_count(request):
    cart = request.session.get('cart', {})
    total_items = sum(cart.values())
    return JsonResponse({'count': total_items})

@login_required
def customer_dashboard(request):
    vendors = Vendor.objects.prefetch_related('icecreams').all() 
    accepted_proposals = FlavorProposal.objects.filter(status='approved').select_related('vendor')
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    
    for product_id, quantity in cart.items():
        if product_id.startswith('proposal_'):
            
            proposal_id = product_id.replace('proposal_', '')
            try:
                proposal = FlavorProposal.objects.get(id=proposal_id, status='approved')
                subtotal = float(proposal.price) * quantity
                total += subtotal
                cart_items.append({
                    'product': proposal,
                    'quantity': quantity,
                    'subtotal': subtotal,
                    'product_id': product_id,
                    'is_proposal': True
                })
            except FlavorProposal.DoesNotExist:
                continue
        else:
            # Handle regular ice cream products
            try:
                product = IceCream.objects.get(id=product_id)
                subtotal = float(product.price) * quantity
                total += subtotal
                cart_items.append({
                    'product': product,
                    'quantity': quantity,
                    'subtotal': subtotal,
                    'product_id': product_id,
                    'is_proposal': False
                })
            except IceCream.DoesNotExist:
                continue
    
    return render(request, 'customer_dashboard.html', {
        'vendors': vendors,  
        'accepted_proposals': accepted_proposals,
        'cart_items': cart_items,
        'cart_total': total
    })

def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(IceCream, id=product_id)
        cart = request.session.get('cart', {})
        
        if str(product_id) in cart:
            cart[str(product_id)] += 1
        else:
            cart[str(product_id)] = 1

        request.session['cart'] = cart
        messages.success(request, f"Added {product.name} to cart!")
        
        return JsonResponse({
            'success': True,
            'message': f'Added {product.name} to cart!',
            'cart_count': sum(cart.values())
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def add_proposal_to_cart(request, proposal_id):
    if request.method == 'POST':
        proposal = get_object_or_404(FlavorProposal, id=proposal_id, status='approved')
        
        cart = request.session.get('cart', {})
        cart_key = f"proposal_{proposal_id}"
        
        if cart_key in cart:
            cart[cart_key] += 1
        else:
            cart[cart_key] = 1

        request.session['cart'] = cart
        messages.success(request, f"Added {proposal.name} to cart!")
        
        return JsonResponse({
            'success': True,
            'message': f'Added {proposal.name} to cart!',
            'cart_count': sum(cart.values())
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def update_cart_quantity(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')  
        
        cart = request.session.get('cart', {})
        
        if product_id in cart:
            if action == 'increase':
                cart[product_id] += 1
            elif action == 'decrease':
                cart[product_id] -= 1
                if cart[product_id] <= 0:
                    del cart[product_id]
        
        request.session['cart'] = cart
        
        return JsonResponse({
            'success': True,
            'new_quantity': cart.get(product_id, 0),
            'cart_count': sum(cart.values())
        })
    
    return JsonResponse({'success': False})


def remove_from_cart(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        cart = request.session.get('cart', {})
        
        if product_id in cart:
            del cart[product_id]
            request.session['cart'] = cart
            messages.success(request, "Item removed from cart!")
        
        return JsonResponse({
            'success': True,
            'cart_count': sum(cart.values())
        })
    
    return JsonResponse({'success': False})


def view_cart(request):
    cart = request.session.get('cart', {})
    items = []
    total = 0

    for product_id, quantity in cart.items():
        if product_id.startswith('proposal_'):
            proposal_id = product_id.replace('proposal_', '')
            try:
                proposal = FlavorProposal.objects.get(id=proposal_id, status='approved')
                subtotal = float(proposal.price) * quantity
                total += subtotal
                items.append({
                    'product': proposal,
                    'quantity': quantity,
                    'subtotal': subtotal,
                    'product_id': product_id,
                    'is_proposal': True
                })
            except FlavorProposal.DoesNotExist:
                continue
        else:
            # Handle regular products
            try:
                product = IceCream.objects.get(id=product_id)
                subtotal = float(product.price) * quantity
                total += subtotal
                items.append({
                    'product': product,
                    'quantity': quantity,
                    'subtotal': subtotal,
                    'product_id': product_id,
                    'is_proposal': False
                })
            except IceCream.DoesNotExist:
                continue

    return render(request, 'cart.html', {'items': items, 'total': total})

@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('view_cart')

    try:
        for product_id, quantity in cart.items():
            if product_id.startswith('proposal_'):
                # Handle proposal checkout
                proposal_id = product_id.replace('proposal_', '')
                proposal = get_object_or_404(FlavorProposal, id=proposal_id, status='approved')
                
                # Check if proposal has enough stock
                if hasattr(proposal, 'stock') and proposal.stock < quantity:
                    messages.error(request, f"Not enough stock for {proposal.name}.")
                    return redirect('view_cart')
                
                # Update proposal stock if it exists
                if hasattr(proposal, 'stock'):
                    proposal.stock -= quantity
                    proposal.save()
                
                # Create a sale record for the proposal
                Sale.objects.create(
                    product=None,  # For proposals, product is None
                    quantity_sold=quantity,
                    customer=request.user,
                    date_sold=timezone.now().date(),
                    # You might want to add a proposal field to Sale model
                )
            else:
                # Handle regular product checkout
                product = get_object_or_404(IceCream, id=product_id)

                if product.stock < quantity:
                    messages.error(request, f"Not enough stock for {product.name}.")
                    return redirect('view_cart')

                product.stock -= quantity
                product.save()

                Sale.objects.create(
                    product=product,
                    quantity_sold=quantity,
                    customer=request.user,
                    date_sold=timezone.now().date()
                )

        request.session['cart'] = {}
        messages.success(request, "Checkout successful!")
        return render(request, 'checkout_success.html')
        
    except Exception as e:
        messages.error(request, "An error occurred during checkout. Please try again.")
        return redirect('view_cart')

@login_required
def update_cart_item(request):
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            
            if quantity <= 0:
                return JsonResponse({
                    'success': False, 
                    'message': 'Invalid quantity'
                }, status=400)
            
            cart = request.session.get('cart', {})
            
            if product_id in cart:
                cart[product_id] = quantity
                request.session['cart'] = cart
                request.session.modified = True
                
                return JsonResponse({
                    'success': True,
                    'message': 'Cart updated',
                    'cart_count': sum(cart.values())
                })
            else:
                return JsonResponse({
                    'success': False, 
                    'message': 'Item not found in cart'
                }, status=404)
                
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({
                'success': False, 
                'message': 'Invalid data'
            }, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


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