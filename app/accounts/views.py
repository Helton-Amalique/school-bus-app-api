from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from core.models import Aluno, Encarregado, Motorista, Gestor, Monitor
from core.serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    AlunoSerializer,
    AlunoCreateSerializer,
    EncarregadoSerializer,
    EncarregadoCreateSerializer,
    MotoristaSerializer,
    MotoristaCreateSerializer,
    GestorSerializer,
    GestorCreateSerializer,
    MonitorSerializer,
    MonitorCreateSerializer,
)
from core.permissions import (
    IsGestor,
    IsMotorista,
    IsMonitor,
    IsEncarregadoDoAluno,
    IsSelfOrAdmin,
)

User = get_user_model()


# ──────────────────────────────────────────────
# PERMISSIONS — definidas aqui para referência
# (ficheiro separado: core/permissions.py)
# ──────────────────────────────────────────────
#
# class IsGestor(BasePermission):
#     def has_permission(self, request, view):
#         return request.user.is_authenticated and request.user.role == 'GESTOR'
#
# class IsMotorista(BasePermission):
#     def has_permission(self, request, view):
#         return request.user.is_authenticated and request.user.role == 'MOTORISTA'
#
# class IsMonitor(BasePermission):
#     def has_permission(self, request, view):
#         return request.user.is_authenticated and request.user.role == 'MONITOR'
#
# class IsSelfOrAdmin(BasePermission):
#     def has_object_permission(self, request, view, obj):
#         return request.user.is_staff or obj.user == request.user
#
# class IsEncarregadoDoAluno(BasePermission):
#     def has_object_permission(self, request, view, obj):
#         return hasattr(request.user, 'encarregado') and obj.encarregado == request.user.encarregado


class UserViewSet(viewsets.ModelViewSet):
    """
    Gestão de utilizadores.
    - Criação: aberta (registo)
    - Leitura/edição do próprio perfil: autenticado
    - Listagem e gestão completa: admin ou gestor
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['nome', 'email']
    ordering_fields = ['nome', 'data_criacao']
    ordering = ['nome']

    def get_queryset(self):
        user = self.request.user
        # Admin e Gestor veem todos
        if user.is_staff or (user.is_authenticated and user.role == 'GESTOR'):
            return User.objects.all()
        # Outros só veem o próprio
        return User.objects.filter(pk=user.pk)

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        if self.action in ('list', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Perfil do utilizador autenticado."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='alterar-password')
    def alterar_password(self, request):
        """Alteração de password autenticada."""
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'mensagem': 'Password alterada com sucesso.'})

    @action(detail=True, methods=['post'], url_path='desativar')
    def desativar(self, request, pk=None):
        """Desativa um utilizador sem o eliminar."""
        if not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'mensagem': f'{user.nome} desativado.'})


class PerfilViewSetMixin:
    """
    Mixin com comportamento comum a todos os ViewSets de perfil:
    - get_serializer_class() alterna entre Create e Read/Update
    - get_permissions() protege escrita para admin/gestor
    - action 'me' devolve o perfil do utilizador autenticado
    """
    create_serializer_class = None
    read_serializer_class = None
    perfil_related_name = None   # ex: 'aluno', 'motorista', 'gestor', 'monitor'

    def get_serializer_class(self):
        if self.action == 'create':
            return self.create_serializer_class
        return self.read_serializer_class

    def get_permissions(self):
        if self.action == 'create':
            return [IsAdminUser()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Perfil do utilizador autenticado (se tiver este role)."""
        perfil = getattr(request.user, self.perfil_related_name, None)
        if not perfil:
            return Response(
                {'erro': 'O utilizador autenticado não tem este perfil.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.read_serializer_class(perfil)
        return Response(serializer.data)


class EncarregadoViewSet(PerfilViewSetMixin, viewsets.ModelViewSet):
    create_serializer_class = EncarregadoCreateSerializer
    read_serializer_class   = EncarregadoSerializer
    perfil_related_name     = 'encarregado'

    filter_backends  = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['ativo']
    search_fields    = ['user__nome', 'user__email', 'nrBI']

    def get_queryset(self):
        return Encarregado.objects.select_related('user').prefetch_related('alunos')

    @action(detail=True, methods=['get'], url_path='alunos')
    def alunos(self, request, pk=None):
        """Lista os alunos de um encarregado."""
        encarregado = self.get_object()
        serializer = AlunoSerializer(encarregado.alunos.all(), many=True)
        return Response(serializer.data)


class AlunoViewSet(PerfilViewSetMixin, viewsets.ModelViewSet):
    create_serializer_class = AlunoCreateSerializer
    read_serializer_class   = AlunoSerializer
    perfil_related_name     = 'aluno'

    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ativo', 'escola_dest', 'classe', 'encarregado']
    search_fields    = ['user__nome', 'user__email', 'nrBI', 'escola_dest']
    ordering_fields  = ['user__nome', 'escola_dest', 'classe']
    ordering         = ['user__nome']

    def get_queryset(self):
        user = self.request.user
        qs = Aluno.objects.select_related('user', 'encarregado__user')

        # Encarregado só vê os seus alunos
        if hasattr(user, 'encarregado'):
            return qs.filter(encarregado=user.encarregado)
        # Aluno só vê o próprio
        if hasattr(user, 'aluno'):
            return qs.filter(user=user)
        return qs

    def get_permissions(self):
        if self.action in ('create', 'destroy'):
            return [IsAdminUser()]
        if self.action in ('update', 'partial_update'):
            return [IsAdminUser() or IsGestor()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'], url_path='rotas')
    def rotas(self, request, pk=None):
        """Rotas de transporte associadas ao aluno."""
        from transporte.serializers import RotaSerializer
        aluno = self.get_object()
        rotas = aluno.rotas_transporte.filter(ativo=True)
        serializer = RotaSerializer(rotas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='com-acesso-bloqueado')
    def com_acesso_bloqueado(self, request):
        """Lista alunos com acesso bloqueado por faturas em atraso."""
        if not (request.user.is_staff or request.user.role in ('GESTOR',)):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bloqueados = [a for a in self.get_queryset() if a.tem_acesso_bloqueado()]
        serializer = self.read_serializer_class(bloqueados, many=True)
        return Response(serializer.data)


class MotoristaViewSet(PerfilViewSetMixin, viewsets.ModelViewSet):
    create_serializer_class = MotoristaCreateSerializer
    read_serializer_class   = MotoristaSerializer
    perfil_related_name     = 'motorista'

    filter_backends  = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ativo']
    search_fields    = ['user__nome', 'user__email', 'nrBI', 'carta_conducao']
    ordering         = ['user__nome']

    def get_queryset(self):
        return Motorista.objects.select_related('user').prefetch_related('veiculos')

    @action(detail=False, methods=['get'], url_path='carta-vencida')
    def carta_vencida(self, request):
        """Lista motoristas com carta de condução vencida."""
        from datetime import date
        vencidos = self.get_queryset().filter(validade_da_carta__lt=date.today())
        serializer = self.read_serializer_class(vencidos, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='veiculos')
    def veiculos(self, request, pk=None):
        """Veículos atribuídos ao motorista."""
        from transporte.serializers import VeiculoListSerializer
        motorista = self.get_object()
        veiculos = motorista.veiculos.filter(ativo=True)
        serializer = VeiculoListSerializer(veiculos, many=True)
        return Response(serializer.data)


class GestorViewSet(PerfilViewSetMixin, viewsets.ModelViewSet):
    create_serializer_class = GestorCreateSerializer
    read_serializer_class   = GestorSerializer
    perfil_related_name     = 'gestor'

    filter_backends  = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['ativo', 'departamento']
    search_fields    = ['user__nome', 'user__email', 'nrBI']

    def get_queryset(self):
        return Gestor.objects.select_related('user').prefetch_related(
            'motoristas_supervisionados__user'
        )

    @action(detail=True, methods=['post'], url_path='adicionar-motorista')
    def adicionar_motorista(self, request, pk=None):
        """Associa um motorista à supervisão deste gestor."""
        gestor = self.get_object()
        motorista_id = request.data.get('motorista_id')
        motorista = get_object_or_404(Motorista, pk=motorista_id)

        if gestor.motoristas_supervisionados.filter(pk=motorista.pk).exists():
            return Response(
                {'erro': f'{motorista} já está sob supervisão deste gestor.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        gestor.motoristas_supervisionados.add(motorista)
        return Response({'mensagem': f'{motorista} adicionado à supervisão.'})

    @action(detail=True, methods=['post'], url_path='remover-motorista')
    def remover_motorista(self, request, pk=None):
        """Remove um motorista da supervisão deste gestor."""
        gestor = self.get_object()
        motorista_id = request.data.get('motorista_id')
        motorista = get_object_or_404(Motorista, pk=motorista_id)
        gestor.motoristas_supervisionados.remove(motorista)
        return Response({'mensagem': f'{motorista} removido da supervisão.'})


class MonitorViewSet(PerfilViewSetMixin, viewsets.ModelViewSet):
    create_serializer_class = MonitorCreateSerializer
    read_serializer_class   = MonitorSerializer
    perfil_related_name     = 'monitor'

    filter_backends  = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['ativo']
    search_fields    = ['user__nome', 'user__email', 'nrBI']

    def get_queryset(self):
        return Monitor.objects.select_related('user').prefetch_related('rotas')

    @action(detail=False, methods=['get'], url_path='sem-rota')
    def sem_rota(self, request):
        """Lista monitores ativos sem rota atribuída."""
        sem_rota = [m for m in self.get_queryset().filter(ativo=True) if not m.tem_rota_ativa()]
        serializer = self.read_serializer_class(sem_rota, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='rota-atual')
    def rota_atual(self, request, pk=None):
        """Rota ativa atual do monitor."""
        from transporte.serializers import RotaSerializer
        monitor = self.get_object()
        rota = monitor.rota_ativa
        if not rota:
            return Response(
                {'mensagem': 'Este monitor não tem rota ativa.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(RotaSerializer(rota).data)
