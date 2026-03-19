"""
transporte/views.py
===================
ViewSets DRF para o módulo transporte.

ViewSets:
  VeiculoViewSet          — CRUD + estatísticas + rotas activas + documentos
  RotaViewSet             — CRUD + alunos (adicionar/remover) + presença
  TransporteAlunoViewSet  — check-in/check-out + resumo diário
  ManutencaoViewSet       — CRUD + concluir + em-curso
  AbastecimentoViewSet    — CRUD + histórico por veículo
"""

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from transporte.filters import (
    AbastecimentoFilter,
    ManutencaoFilter,
    TransporteAlunoFilter,
)
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from core.permissions import (
    IsGestor,
    IsGestorOuMotorista,
    IsGestorOuMotoristaOuMonitor,
    PodeVerRota,
    PodeVerVeiculo,
)
from rest_framework.response import Response

from core.models import Aluno
from transporte.models import Abastecimento, Manutencao, Rota, TransporteAluno, Veiculo
from transporte.serializers import (
    AbastecimentoSerializer,
    CheckInSerializer,
    ManutencaoConcluirSerializer,
    ManutencaoSerializer,
    RotaSerializer,
    RotaWriteSerializer,
    TransporteAlunoSerializer,
    VeiculoListSerializer,
    VeiculoSerializer,
    VeiculoWriteSerializer,
)


class VeiculoViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ativo', 'marca', 'motorista']
    search_fields = ['matricula', 'marca', 'modelo', 'motorista__user__nome']
    ordering_fields = ['matricula', 'quilometragem_atual', 'capacidade']
    ordering = ['matricula']

    def get_queryset(self):
        return (
            Veiculo.objects
            .select_related('motorista__user')
            .prefetch_related('rotas', 'manutencoes', 'abastecimento')
            .annotate(
                alunos_count=Count(
                    'rotas__alunos',
                    filter=Q(rotas__ativo=True)
                )
            )
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return VeiculoListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return VeiculoWriteSerializer
        return VeiculoSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsGestor()]
        if self.action in ('retrieve', 'estatisticas', 'rotas_ativas',
                           'manutencoes', 'abastecimentos'):
            return [PodeVerVeiculo()]
        return [IsGestorOuMotoristaOuMonitor()]

    def perform_destroy(self, instance):
        """Soft delete — desactiva o veículo sem apagar."""
        instance.ativo = False
        instance.save(update_fields=['ativo'])

    # ── Actions ──────────────────────────────

    @action(detail=True, methods=['get'], url_path='estatisticas')
    def estatisticas(self, request, pk=None):
        """
        Métricas calculadas do veículo:
        consumo médio, custo/km, autonomia, estado de manutenção e documentação.
        """
        veiculo = self.get_object()
        return Response({
            'matricula': veiculo.matricula,
            'quilometragem_atual': veiculo.quilometragem_atual,
            'consumo_medio_km_l': round(veiculo.consumo_medio(), 2),
            'custo_por_km_mzn': veiculo.custo_por_quilometro(),
            'autonomia_estimada_km': veiculo.autonomia_estimada,
            'custo_total_combustivel_mzn': float(veiculo.custo_total_combustivel),
            'vagas_disponiveis': veiculo.vagas_disponiveis,
            'em_manutencao': veiculo.em_manutencao(),
            'precisa_manutencao': veiculo.precisa_manutencao(),
            'documentacao_em_dia': veiculo.document_em_dia(),
        })

    @action(detail=True, methods=['get'], url_path='rotas-ativas')
    def rotas_ativas(self, request, pk=None):
        """Lista as rotas activas do veículo."""
        veiculo = self.get_object()
        rotas = veiculo.rotas.filter(ativo=True).select_related('veiculo__motorista__user')
        serializer = RotaSerializer(rotas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='manutencoes')
    def manutencoes(self, request, pk=None):
        """Histórico completo de manutenções do veículo."""
        veiculo = self.get_object()
        qs = veiculo.manutencoes.all().order_by('-data_inicio')
        serializer = ManutencaoSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='abastecimentos')
    def abastecimentos(self, request, pk=None):
        """Histórico completo de abastecimentos do veículo."""
        veiculo = self.get_object()
        qs = veiculo.abastecimento.all().order_by('-data')
        serializer = AbastecimentoSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='a-precisar-revisao')
    def a_precisar_revisao(self, request):
        """
        Veículos activos que precisam de revisão (baseado em quilometragem).
        Não inclui os que já estão em manutenção.
        """
        veiculos = [v for v in self.get_queryset().filter(ativo=True) if v.precisa_manutencao()]
        serializer = VeiculoListSerializer(veiculos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='documentos-a-vencer')
    def documentos_a_vencer(self, request):
        """
        Veículos activos com seguro, inspecção ou manifesto
        a expirar nos próximos 30 dias (ou já expirados).
        """
        import datetime
        limite = datetime.date.today() + datetime.timedelta(days=30)
        qs = self.get_queryset().filter(
            ativo=True,
        ).filter(
            Q(data_validade_seguro__lte=limite) | Q(data_validade_inspecao__lte=limite) | Q(data_validade_manifesto__lte=limite)
        )
        serializer = VeiculoListSerializer(qs, many=True)
        return Response(serializer.data)


class RotaViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ativo', 'veiculo', 'veiculo__marca']
    search_fields = ['nome', 'veiculo__matricula', 'veiculo__motorista__user__nome']
    ordering_fields = ['nome', 'hora_partida']
    ordering = ['nome']

    def get_queryset(self):
        return (
            Rota.objects
            .select_related('veiculo__motorista__user')
            .prefetch_related('alunos__user')
            .annotate(total_inscritos_ann=Count('alunos'))
        )

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RotaWriteSerializer
        return RotaSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy',
                           'adicionar_aluno', 'remover_aluno'):
            return [IsGestor()]
        if self.action in ('retrieve', 'alunos', 'presenca_hoje', 'resumo_hoje'):
            return [PodeVerRota()]
        return [IsGestorOuMotoristaOuMonitor()]

    def perform_destroy(self, instance):
        instance.ativo = False
        instance.save(update_fields=['ativo'])

    # ── Actions ──────────────────────────────

    @action(detail=True, methods=['get'], url_path='alunos')
    def listar_alunos(self, request, pk=None):
        """Lista os alunos inscritos na rota."""
        from core.serializers import AlunoListSerializer
        rota = self.get_object()
        serializer = AlunoListSerializer(
            rota.alunos.filter(ativo=True).select_related('user', 'encarregado__user'),
            many=True
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='adicionar-aluno')
    def adicionar_aluno(self, request, pk=None):
        """Inscreve um aluno activo na rota, verificando capacidade e duplicados."""
        rota = self.get_object()
        aluno_id = request.data.get('aluno_id')

        if not aluno_id:
            return Response(
                {'erro': 'aluno_id é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        aluno = get_object_or_404(Aluno, pk=aluno_id, ativo=True)

        if rota.alunos.filter(pk=aluno.pk).exists():
            return Response(
                {'erro': f'{aluno} já está inscrito nesta rota.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if rota.alunos.count() >= rota.veiculo.capacidade:
            return Response(
                {'erro': f'Capacidade do veículo ({rota.veiculo.capacidade}) atingida.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rota.alunos.add(aluno)
        return Response(
            {'mensagem': f'{aluno} inscrito na rota {rota.nome}.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='remover-aluno')
    def remover_aluno(self, request, pk=None):
        """Remove um aluno da rota."""
        rota = self.get_object()
        aluno_id = request.data.get('aluno_id')

        if not aluno_id:
            return Response(
                {'erro': 'aluno_id é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        aluno = get_object_or_404(Aluno, pk=aluno_id)

        if not rota.alunos.filter(pk=aluno.pk).exists():
            return Response(
                {'erro': f'{aluno} não está inscrito nesta rota.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rota.alunos.remove(aluno)
        return Response(
            {'mensagem': f'{aluno} removido da rota {rota.nome}.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'], url_path='presenca-hoje')
    def presenca_hoje(self, request, pk=None):
        """Lista os registos de TransporteAluno desta rota para hoje."""
        rota = self.get_object()
        qs = TransporteAluno.objects.filter(
            rota=rota,
            data=timezone.localdate()
        ).select_related('aluno__user')
        serializer = TransporteAlunoSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='resumo-hoje')
    def resumo_hoje(self, request, pk=None):
        """Contagem por status para o painel do motorista."""
        rota = self.get_object()
        resumo = (
            TransporteAluno.objects
            .filter(rota=rota, data=timezone.localdate())
            .values('status')
            .annotate(total=Count('id'))
        )
        return Response(list(resumo))


class TransporteAlunoViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = TransporteAlunoFilter
    ordering = ['-data']

    def get_queryset(self):
        user = self.request.user
        qs = TransporteAluno.objects.select_related(
            'aluno__user',
            'rota__veiculo__motorista__user'
        )

        try:
            motorista = user.perfil_motorista
            return qs.filter(rota__veiculo__motorista=motorista)
        except ObjectDoesNotExist:
            pass
        try:
            monitor = user.perfil_monitor
            rota_ativa = monitor.rota_ativa
            if rota_ativa:
                return qs.filter(rota=rota_ativa)
        except ObjectDoesNotExist:
            pass
        try:
            encarregado = user.perfil_encarregado
            return qs.filter(aluno__encarregado=encarregado)
        except ObjectDoesNotExist:
            pass
        return qs

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return CheckInSerializer
        return TransporteAlunoSerializer

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsGestor()]
        return [IsGestorOuMotoristaOuMonitor()]

    # ── Actions ──────────────────────────────

    @action(detail=True, methods=['post'], url_path='check-in')
    def check_in(self, request, pk=None):

        registo = self.get_object()
        serializer = CheckInSerializer(
            registo,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='hoje')
    def hoje(self, request):
        """Registos do dia actual para o utilizador autenticado."""
        qs = self.get_queryset().filter(data=timezone.localdate())
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='resumo-hoje')
    def resumo_hoje(self, request):
        """Contagem por status para o dashboard do motorista/monitor."""
        resumo = (
            self.get_queryset()
            .filter(data=timezone.localdate())
            .values('status')
            .annotate(total=Count('id'))
        )
        return Response(list(resumo))


class ManutencaoViewSet(viewsets.ModelViewSet):

    serializer_class = ManutencaoSerializer
    permission_classes = [IsGestor]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ManutencaoFilter
    ordering = ['-data_inicio']

    def get_queryset(self):
        return Manutencao.objects.select_related('veiculo__motorista__user')

    # ── Actions ──────────────────────────────

    @action(detail=True, methods=['post'], url_path='concluir')
    def concluir(self, request, pk=None):
        """
        Conclui uma manutenção, actualiza a quilometragem do veículo
        e agenda a próxima revisão.
        """
        manutencao = self.get_object()

        if manutencao.concluida:
            return Response(
                {'erro': 'Esta manutenção já foi concluída.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ManutencaoConcluirSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            manutencao.concluir_manutencao(
                km_proximo_ajuste=serializer.validated_data['km_proximo_ajuste']
            )
        except Exception as e:
            return Response({'erro': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ManutencaoSerializer(manutencao).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='em-curso')
    def em_curso(self, request):
        """Lista manutenções ainda não concluídas."""
        qs = self.get_queryset().filter(concluida=False)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class AbastecimentoViewSet(viewsets.ModelViewSet):

    serializer_class = AbastecimentoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = AbastecimentoFilter
    ordering = ['-data', '-quilometragem_no_ato']

    def get_queryset(self):
        return Abastecimento.objects.select_related('veiculo__motorista__user')

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsGestor()]
        if self.action == 'create':
            return [IsGestorOuMotorista()]
        return [IsGestorOuMotorista()]

    # ── Actions ──────────────────────────────

    @action(detail=False, methods=['get'], url_path='resumo-frota')
    def resumo_frota(self, request):
        """
        Agrega custo total e litros por veículo.
        Útil para o dashboard financeiro da frota.
        """
        from django.db.models import Sum
        resumo = (
            self.get_queryset()
            .values('veiculo__matricula', 'veiculo__marca', 'veiculo__modelo')
            .annotate(
                total_litros=Sum('quantidade_litros'),
                total_custo=Sum('custo_total'),
            )
            .order_by('veiculo__matricula')
        )
        return Response(list(resumo))
