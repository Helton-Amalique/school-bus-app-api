from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from transporte.models import Veiculo, Rota, TransporteAluno, Manutencao
from transporte.serializers import VeiculoSerializer, RotaSerializer, CheckInSerializer, ManutencaoSerializer
from accounts.permissions import IsAdmin, IsMotorista

class VeiculoViewSet(viewsets.ModelViewSet):
    queryset = Veiculo.objects.all()
    serializer_class = VeiculoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Veiculo.objects.none()
        if user.role == 'ADMIN':
            return Veiculo.objects.all()
        return Veiculo.objects.filter(motorista__user=user)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [(IsAdmin | IsMotorista)()]
        return [IsAdmin()]

class RotaViewSet(viewsets.ModelViewSet):
    serializer_class = RotaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Rota.objects.none()
        if user.role == 'ADMIN':
            return Rota.objects.all()
        return Rota.objects.filter(veiculo__motorista__user=user)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [(IsAdmin | IsMotorista)()]
        return [IsAdmin()]
class TransportViewSet(viewsets.ModelViewSet):
    serializer_class = CheckInSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return TransporteAluno.objects.none()
        if user.role == "ADMIN":
            return TransporteAluno.objects.all()
        return TransporteAluno.objects.filter(rota__veiculo__motorista__user=user)

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'partial_update']:
            return [(IsAdmin | IsMotorista)()]
        return [IsAdmin()]


class ManutencaoViewSet(viewsets.ModelViewSet):
    serializer_class = ManutencaoSerializer
    queryset = Manutencao.objects.all().select_related('veiculo')
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"], url_path='concluir')
    def concluir(self, request, pk=None):
        manutencao = self.get_object()
        if manutencao.concluida:
            return Response(
                {"erro,", "Esta manuntencao ja foi concluida anteriormente."},
                status=status.HTTP_400_BAD_REQUEST
            )
        manutencao.concluir_manutencao()

        return Response(
            {
                "status": "Manutencao concluida com sucesso.",
                "veiculo": manutencao.veiculo.matricula,
                "proxima_revisao": manutencao.veiculo.km_proxima_revisao,
                "sucesso": True},
            status=status.HTTP_200_OK
        )
