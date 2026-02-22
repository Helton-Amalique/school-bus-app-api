from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView, TokenVerifyView)
from accounts.views import CreateUserView, CreateTokenView, ManageUserView

app_name = 'accounts'

router = DefaultRouter()
# router.register(r"users", views.UserViewSet.as_view, basename="user")

urlpatterns = [
    path('create/', CreateUserView.as_view(), name='create_user'),
    path('token/', CreateTokenView.as_view(), name='token'),
    path('me/', ManageUserView.as_view(), name='me'),

    # path("", include(router.urls)),
]
