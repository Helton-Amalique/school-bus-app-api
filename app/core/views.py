"""
core/views.py
=============
ViewSets DRF para o módulo core.

ViewSets:
  UserViewSet          — perfil próprio + gestão de utilizadores (admin)
  EncarregadoViewSet   — CRUD + alunos do encarregado
  AlunoViewSet         — CRUD + rotas + estado financeiro
  MotoristaViewSet     — CRUD + veículos + carta
  GestorViewSet        — CRUD + motoristas supervisionados
  MonitorViewSet       — CRUD + rota activa

Permissões globais:
  - Leitura:  IsAuthenticated
  - Escrita:  IsGestor  (salvo actions explícitas)
  - /me:      qualquer utilizador autenticado (próprio perfil)
"""

from django.db.models import Count, Prefetch
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from core.permissions import (
    IsGestor,
    IsGestorOuEncarregado,
    IsGestorOuMotoristaOuMonitor,
    IsGestorOuProprioAluno,
    IsProprioPerfilOuGestor,
    PodeLerMensalidade,
    PodeVerRota,
)
from rest_framework.response import Response

from core.models import Aluno, Encarregado, Gestor, Monitor, Motorista, User
from core.serializers import (
    AlunoListSerializer,
    AlunoSerializer,
    AlunoWriteSerializer,
    ChangePasswordSerializer,
    EncarregadoSerializer,
    EncarregadoWriteSerializer,
    GestorSerializer,
    GestorWriteSerializer,
    MonitorListSerializer,
    MonitorSerializer,
    MonitorWriteSerializer,
    MotoristaListSerializer,
    MotoristaSerializer,
    MotoristaWriteSerializer,
    UserSerializer,
)


def _perfil_do_user(user):
    """
    Devolve o perfil de core associado ao utilizador autenticado.
    Usado nas actions /me dos ViewSets de perfil.
    """
    PERFIL_ATTR = {
        'ALUNO': 'perfil_aluno',
        'MOTORISTA': 'perfil_motorista',
        'MONITOR': 'perfil_monitor',
        'GESTOR': 'perfil_gestor',
        'ENCARREGADO': 'perfil_encarregado',
    }
    attr = PERFIL_ATTR.get(user.role)
    if not attr:
        return None
    return getattr(user, attr, None)


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Gestão de utilizadores.

    GET  /users/          → lista (admin)
    GET  /users/{id}/     → detalhe (admin)
    GET  /users/me/       → perfil próprio
    POST /users/me/change-password/ → alterar senha
    POST /users/{id}/desativar/     → desactivar utilizador (admin)
    POST /users/{id}/ativar/        → reactivar utilizador (admin)
    """

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['nome', 'email']
    ordering_fields = ['nome', 'data_criacao']
    ordering = ['nome']

    def get_queryset(self):
        return User.objects.all()

    def get_permissions(self):
        if self.action in ('me', 'change_password'):
            return [IsAuthenticated()]
        if self.action in ('list', 'retrieve', 'testar_sms'):
            return [IsGestor()]
        # desativar, ativar, criar, editar
        return [IsGestor()]

    # ── /me ──────────────────────────────────

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Devolve os dados do utilizador autenticado."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='me/change-password')
    def change_password(self, request):
        """Altera a senha do utilizador autenticado."""
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'mensagem': 'Senha alterada com sucesso.'})

    # ── Activação / Desactivação ──────────────

    @action(detail=False, methods=['post'], url_path='testar-sms')
    def testar_sms(self, request):
        """
        Envia um SMS de teste de forma assíncrona via Celery.
        O request retorna imediatamente com 202 — o Worker processa em background.
        Verificar os logs do worker para o resultado real.

        POST /api/v1/users/testar-sms/
        Payload: { "numero": "+258841234567", "mensagem": "Teste" }
        """
        numero = request.data.get('numero')
        mensagem = request.data.get('mensagem', 'Teste do Sistema de Transporte Escolar')

        if not numero:
            return Response(
                {'erro': 'Campo "numero" é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from financeiro.tasks import enviar_sms_manual_task
        task = enviar_sms_manual_task.delay(numero, mensagem)

        return Response(
            {
                'sucesso': True,
                'mensagem': 'Tarefa de envio enviada para o Worker.',
                'task_id': task.id,
                'detalhe': f'SMS para {numero} em processamento. Verifique os logs do worker.',
            },
            status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=['post'], url_path='desativar')
    def desativar(self, request, pk=None):
        """Desactiva um utilizador (soft-disable)."""
        user = self.get_object()
        if not user.is_active:
            return Response(
                {'erro': 'O utilizador já está inactivo.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({'mensagem': f'Utilizador {user.nome} desactivado.'})

    @action(detail=True, methods=['post'], url_path='ativar')
    def ativar(self, request, pk=None):
        """Reactiva um utilizador."""
        user = self.get_object()
        if user.is_active:
            return Response(
                {'erro': 'O utilizador já está activo.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'mensagem': f'Utilizador {user.nome} activado.'})


class EncarregadoViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ativo']
    search_fields = ['user__nome', 'user__email', 'nrBI']
    ordering_fields = ['user__nome', 'criado_em']
    ordering = ['user__nome']

    def get_queryset(self):
        return (
            Encarregado.objects
            .select_related('user')
            .prefetch_related('alunos__user')
            .annotate(total_alunos=Count('alunos'))
        )

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return EncarregadoWriteSerializer
        return EncarregadoSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy',
                           'desativar', 'ativar'):
            return [IsGestor()]
        # lista, detalhe, /me, /alunos
        return [IsGestorOuEncarregado()]

    def perform_destroy(self, instance):
        """Soft delete — desactiva o encarregado e o utilizador associado."""
        instance.ativo = False
        instance.save(update_fields=['ativo'])
        instance.user.is_active = False
        instance.user.save(update_fields=['is_active'])

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Perfil do encarregado autenticado."""
        perfil = _perfil_do_user(request.user)
        if not perfil or request.user.role != 'ENCARREGADO':
            return Response(
                {'erro': 'Perfil de encarregado não encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = EncarregadoSerializer(perfil)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='alunos')
    def alunos(self, request, pk=None):
        """Lista os alunos activos do encarregado."""
        encarregado = self.get_object()
        alunos = encarregado.alunos.filter(ativo=True).select_related('user')
        serializer = AlunoListSerializer(alunos, many=True)
        return Response(serializer.data)


class AlunoViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ativo', 'escola_dest', 'classe', 'encarregado']
    search_fields = ['user__nome', 'user__email', 'nrBI', 'escola_dest']
    ordering_fields = ['user__nome', 'escola_dest', 'classe', 'criado_em']
    ordering = ['user__nome']

    def get_queryset(self):
        return (
            Aluno.objects
            .select_related('user', 'encarregado__user')
            .prefetch_related('rotas_transporte__veiculo__motorista__user')
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return AlunoListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return AlunoWriteSerializer
        return AlunoSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsGestor()]
        if self.action in ('retrieve',):
            return [IsGestorOuProprioAluno()]
        if self.action == 'financeiro':
            return [IsGestorOuEncarregado()]
        # list, me, rotas
        return [IsGestorOuMotoristaOuMonitor()]

    def perform_destroy(self, instance):
        instance.ativo = False
        instance.save(update_fields=['ativo'])
        instance.user.is_active = False
        instance.user.save(update_fields=['is_active'])

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Perfil do aluno autenticado."""
        perfil = _perfil_do_user(request.user)
        if not perfil or request.user.role != 'ALUNO':
            return Response(
                {'erro': 'Perfil de aluno não encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = AlunoSerializer(perfil)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='rotas')
    def rotas(self, request, pk=None):
        """Rotas de transporte activas do aluno."""
        from transporte.serializers import RotaSerializer
        aluno = self.get_object()
        rotas = aluno.rotas_transporte.filter(ativo=True).select_related(
            'veiculo__motorista__user'
        )
        serializer = RotaSerializer(rotas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='financeiro')
    def financeiro(self, request, pk=None):
        """
        Resumo financeiro do aluno: mensalidades em atraso,
        saldo devedor e estado de acesso.
        """
        from financeiro.models import Mensalidade
        aluno = self.get_object()

        mensalidades = Mensalidade.objects.filter(aluno=aluno).order_by('-mes_referente')
        em_atraso = mensalidades.filter(estado='ATRASADO')
        bloqueado = Mensalidade.objects.aluno_tem_acesso_bloqueado(aluno)

        return Response({
            'aluno_id': aluno.pk,
            'nome': aluno.user.nome,
            'acesso_bloqueado': bloqueado,
            'mensalidades_em_atraso': em_atraso.count(),
            'saldo_devedor_total': sum(m.saldo_devedor for m in em_atraso),
            'ultima_mensalidade': (
                str(mensalidades.first().mes_referente.strftime('%m/%Y'))
                if mensalidades.exists() else None
            ),
        })


class MotoristaViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ativo']
    search_fields = ['user__nome', 'user__email', 'nrBI', 'carta_conducao']
    ordering_fields = ['user__nome', 'validade_da_carta', 'criado_em']
    ordering = ['user__nome']

    def get_queryset(self):
        return (
            Motorista.objects
            .select_related('user')
            .prefetch_related('veiculos', 'gestores__user')
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return MotoristaListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return MotoristaWriteSerializer
        return MotoristaSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsGestor()]
        if self.action in ('me', 'veiculos', 'carta_a_vencer'):
            return [IsProprioPerfilOuGestor()]
        # list, retrieve
        return [IsGestor()]

    def perform_destroy(self, instance):
        instance.ativo = False
        instance.save(update_fields=['ativo'])
        instance.user.is_active = False
        instance.user.save(update_fields=['is_active'])

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Perfil do motorista autenticado."""
        perfil = _perfil_do_user(request.user)
        if not perfil or request.user.role != 'MOTORISTA':
            return Response(
                {'erro': 'Perfil de motorista não encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = MotoristaSerializer(perfil)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='veiculos')
    def veiculos(self, request, pk=None):
        """Veículos activos atribuídos ao motorista."""
        from transporte.serializers import VeiculoListSerializer
        motorista = self.get_object()
        veiculos = motorista.veiculos.filter(ativo=True)
        serializer = VeiculoListSerializer(veiculos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='carta-a-vencer')
    def carta_a_vencer(self, request):
        """
        Motoristas com carta de condução a vencer nos próximos 30 dias
        (ou já vencida). Útil para alertas no dashboard.
        """
        from datetime import date, timedelta
        limite = date.today() + timedelta(days=30)
        qs = self.get_queryset().filter(
            ativo=True,
            validade_da_carta__lte=limite,
        )
        serializer = MotoristaListSerializer(qs, many=True)
        return Response(serializer.data)


class GestorViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ativo', 'departamento']
    search_fields = ['user__nome', 'user__email', 'nrBI']
    ordering_fields = ['user__nome', 'departamento', 'criado_em']
    ordering = ['user__nome']

    def get_queryset(self):
        return (
            Gestor.objects
            .select_related('user')
            .prefetch_related('motoristas_supervisionados__user')
        )

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return GestorWriteSerializer
        return GestorSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy',
                           'adicionar_motorista', 'remover_motorista'):
            return [IsGestor()]
        if self.action == 'me':
            return [IsAuthenticated()]
        return [IsGestor()]

    def perform_destroy(self, instance):
        instance.ativo = False
        instance.save(update_fields=['ativo'])
        instance.user.is_active = False
        instance.user.save(update_fields=['is_active'])

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Perfil do gestor autenticado."""
        perfil = _perfil_do_user(request.user)
        if not perfil or request.user.role != 'GESTOR':
            return Response(
                {'erro': 'Perfil de gestor não encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = GestorSerializer(perfil)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='adicionar-motorista')
    def adicionar_motorista(self, request, pk=None):
        """Associa um motorista activo à supervisão deste gestor."""
        gestor     = self.get_object()
        motorista_id = request.data.get('motorista_id')

        if not motorista_id:
            return Response(
                {'erro': 'motorista_id é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            motorista = Motorista.objects.get(pk=motorista_id, ativo=True)
        except Motorista.DoesNotExist:
            return Response(
                {'erro': 'Motorista não encontrado ou inactivo.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if gestor.motoristas_supervisionados.filter(pk=motorista.pk).exists():
            return Response(
                {'erro': f'{motorista} já está sob supervisão deste gestor.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        gestor.motoristas_supervisionados.add(motorista)
        return Response({'mensagem': f'{motorista} adicionado à supervisão.'})

    @action(detail=True, methods=['post'], url_path='remover-motorista')
    def remover_motorista(self, request, pk=None):
        gestor = self.get_object()
        motorista_id = request.data.get('motorista_id')

        if not motorista_id:
            return Response(
                {'erro': 'motorista_id é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            motorista = Motorista.objects.get(pk=motorista_id)
        except Motorista.DoesNotExist:
            return Response({'erro': 'Motorista não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not gestor.motoristas_supervisionados.filter(pk=motorista.pk).exists():
            return Response(
                {'erro': f'{motorista} não está sob supervisão deste gestor.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        gestor.motoristas_supervisionados.remove(motorista)
        return Response({'mensagem': f'{motorista} removido da supervisão.'})


class MonitorViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ativo']
    search_fields = ['user__nome', 'user__email', 'nrBI']
    ordering_fields = ['user__nome', 'criado_em']
    ordering = ['user__nome']

    def get_queryset(self):
        return (
            Monitor.objects
            .select_related('user')
            .prefetch_related('rotas__veiculo__motorista__user')
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return MonitorListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return MonitorWriteSerializer
        return MonitorSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsGestor()]
        if self.action == 'me':
            return [IsAuthenticated()]
        # list, retrieve, rota_ativa
        return [IsGestorOuMotoristaOuMonitor()]

    def perform_destroy(self, instance):
        instance.ativo = False
        instance.save(update_fields=['ativo'])
        instance.user.is_active = False
        instance.user.save(update_fields=['is_active'])

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Perfil do monitor autenticado."""
        perfil = _perfil_do_user(request.user)
        if not perfil or request.user.role != 'MONITOR':
            return Response(
                {'erro': 'Perfil de monitor não encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = MonitorSerializer(perfil)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='rota')
    def rota_ativa(self, request, pk=None):
        """Rota activa actual do monitor."""
        from transporte.serializers import RotaSerializer
        monitor = self.get_object()
        rota    = monitor.rota_ativa

        if not rota:
            return Response(
                {'mensagem': 'Este monitor não tem rota activa.'},
                status=status.HTTP_200_OK
            )
        serializer = RotaSerializer(rota)
        return Response(serializer.data)
