"""Views for the accounts app."""

from rest_framework import generics, authentication, permissions
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from accounts.serializers import UserSerializer, AuthTokenSerializer


class CreateUserView(generics.CreateAPIView):
    """View para criar um novo usuário."""
    serializer_class = UserSerializer
    # permission_classes = [AllowAny]


class CreateTokenView(ObtainAuthToken):
    """Create a new auth token"""
    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES


class ManageUserView(generics.RetrieveUpdateAPIView):
    """"""
    serializer_class = UserSerializer
    authentication_class = [authentication.TokenAuthentication]
    permissions_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """retrieve and retr"""
        return self.request.user

# from rest_framework.viewsets import ModelViewSet
# from accounts.models import User
# from accounts.serializers import UserSerializer
# from accounts.permissions import IsAdmin

# class UserViewSet(ModelViewSet):
#     queryset = User.objects.all()
#     serializer_class = UserSerializer

#     def get_queryset(self):
#         user = self.request.user
#         if user.role == "ADMIN":
#             return User.objects.all()
#         # cada usuário só vê a si mesmo
#         return User.objects.filter(id=user.id)

#     def get_permissions(self):
#         if self.action in ["list", "retrieve"]:
#             return [IsAdmin()]
#         elif self.action in ["create", "update", "partial_update", "destroy"]:
#             return [IsAdmin()]
#         return super().get_permissions()
