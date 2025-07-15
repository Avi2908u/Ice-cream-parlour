from django.urls import path
from .views import (
    RegisterView, UserListView, SummaryView,
    login_page, signup_page
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # JWT API endpoints
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/users/', UserListView.as_view(), name='user-list'),
    path('api/summary/', SummaryView.as_view(), name='summary'),

    # Web UI views (login/signup pages)
    path('', signup_page, name='signup'),          # Default route = signup page
    path('signup/', signup_page, name='signup'),
    path('login/', login_page, name='login'),
]
