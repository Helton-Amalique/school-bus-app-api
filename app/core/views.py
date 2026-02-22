from accounts.models import User
from core.models import Aluno, Motorista, Encarregado
from core.serializers import AlunoSerializer, MotoristaSerializer, EncarregadoSerializer
from accounts.permissions import IsAdmin, IsMotorista, IsEncarregado, IsAluno

from rest_framework.viewsets import ModelViewSet


class AlunoViewSet(ModelViewSet):
    queryset = Aluno.objects.all()
    serializer_class = AlunoSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Aluno.objects.none()

        if user.role == User.Cargo.ADMIN:
            return Aluno.objects.all()
        elif user.role == User.Cargo.ENCARREGADO:
            return Aluno.objects.filter(encarregado__user=user).select_related('user', 'encarregado')
        elif user.role == User.Cargo.ALUNO:
            return Aluno.objects.filter(user=user)
        return Aluno.objects.none()

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAdmin(), IsEncarregado(), IsAluno()]
        return [IsAdmin()]


class MotoristaViewSet(ModelViewSet):
    queryset = Motorista.objects.all()
    serializer_class = MotoristaSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Motorista.objects.none()

        if user.role == User.Cargo.ADMIN:
            return Motorista.objects.all()
        elif user.role == User.Cargo.MOTORISTA:
            return Motorista.objects.filter(user=user)
        return Motorista.objects.none()

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAdmin(), IsMotorista()]
        return [IsAdmin()]


class EncarregadoViewSet(ModelViewSet):
    queryset = Encarregado.objects.all()
    serializer_class = EncarregadoSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Encarregado.objects.none()

        if user.role == User.Cargo.ADMIN:
            return Encarregado.objects.all()
        elif user.role == User.Cargo.ENCARREGADO:
            return Encarregado.objects.filter(user=user)
        return Encarregado.objects.none()

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAdmin(), IsEncarregado(), IsAluno()]
        return [IsAdmin()]
