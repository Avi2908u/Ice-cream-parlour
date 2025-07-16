from django.urls import path
from . import views
from .views import RegisterView, UserListView, SummaryView 
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


urlpatterns = [
    path('', views.login_page, name='index'),
    path('signup/', views.signup_page, name='signup'),
    path('login/', views.login_page, name='login'),
    path('owner/', views.owner_dashboard, name='owner_dashboard'),
    path('vendor/', views.vendor_dashboard, name='vendor_dashboard'),
    path('customer/', views.customer_dashboard, name='customer_dashboard'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('api/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/', UserListView.as_view(), name='user-list'), 
    path('summary/', SummaryView.as_view(), name='summary'),
    path('submit_flavour_proposal/',views.submit_flavour_proposal,name='submit_flavour_proposal')
]
