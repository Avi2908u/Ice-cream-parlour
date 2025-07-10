from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('owner/', views.owner_dashboard, name='owner'),
    path('vendor/', views.vendor_dashboard, name='vendor'),
    path('customer/', views.customer_dashboard, name='customer'),
]
