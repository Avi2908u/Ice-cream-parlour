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



    path('vendor/login/', views.vendor_login, name='vendor_login'),
    path('vendor/logout/', views.vendor_logout, name='vendor_logout'),
    path('vendor/register/', views.vendor_register, name='vendor_register'),
    path('vendor/dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('vendor/products/', views.vendor_products, name='vendor_products'),
    path('vendor/products/add/', views.add_product, name='add_product'),
    path('vendor/products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('vendor/products/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('vendor/orders/', views.vendor_orders, name='vendor_orders'),
    path('vendor/orders/update/<int:order_id>/', views.update_order_status, name='update_order_status'),
    
    # API URLs for real-time updates
    path('vendor/api/stats/', views.api_vendor_stats, name='api_vendor_stats'),
    path('vendor/api/products/', views.api_vendor_products, name='api_vendor_products'),
    
    # Customer URLs
    path('products/', views.customer_products, name='customer_products'),
    path('purchase/', views.purchase_product, name='purchase_product'),
    
    # Home page
    path('', views.customer_products, name='home'),
]
