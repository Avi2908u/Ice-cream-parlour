from django.urls import path
from .views import RegisterView, UserListView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import SummaryView
from . import views
from authapp import views as auth_views

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/', UserListView.as_view(), name='user-list'), 
    path('summary/', SummaryView.as_view(), name='summary'),
    path('login/', views.login_page, name='login'),

    path('', auth_views.login_page, name='home'),
]
