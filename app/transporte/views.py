from rest_framework import viewsets, permissions
from transporte.models import Veiculo, Rota, TransporteAluno
from transporte.serializers import VeiculoSerializer, RotaSerializer, CheckInSerializer
from accounts.permissions import IsAdmin, IsMotorista

class VeiculoViewSet(viewsets.ModelViewSet):
    queryset = Veiculo.objects.all()
    serializer_class = VeiculoSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Veiculo.objects.none()
        if user.role == 'ADMIN':
            return Veiculo.objects.all()
        return Veiculo.objects.filter(motorista__user=user)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAdmin() | IsMotorista()]
        return [IsAdmin()]

class RotaViewSet(viewsets.ModelViewSet):
    serializer_class = RotaSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Rota.objects.none()
        if user.role == 'ADMIN':
            return Rota.objects.all()
        return Rota.objects.filter(veiculo__motorista__user=user)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAdmin() | IsMotorista()]
        return [IsAdmin()]

class TransportViewSet(viewsets.ModelViewSet):
    serializer_class = CheckInSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return TransporteAluno.objects.none()
        if user.role == "ADMIN":
            return TransporteAluno.objects.all()
        return TransporteAluno.objects.filter(rota__veiculo__motorista__user=user)

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'partial_update']:
            return [IsAdmin() | IsMotorista()]
        return [IsAdmin()]
