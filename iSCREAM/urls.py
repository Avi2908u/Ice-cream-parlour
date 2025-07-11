from django.urls import path
from . import views

app_name = 'cart'  # Needed if using namespaced URLs like 'cart:view_cart'

urlpatterns = [
    path('', views.index, name='index'),
    path('owner/', views.owner_dashboard, name='owner_dashboard'),
    path('vendor/', views.vendor_dashboard, name='vendor_dashboard'),
    path('customer/', views.customer_dashboard, name='customer_dashboard'),
    path('products/', views.product_list, name='product_list'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('checkout/', views.checkout, name='checkout'),
]
