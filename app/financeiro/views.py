"""
financeiro/views.py
===================
ViewSets DRF para o módulo financeiro.

ViewSets:
  ConfiguracaoFinanceiraViewSet  — leitura e edição do singleton
  CategoriaViewSet               — CRUD de categorias
  TransacaoViewSet               — CRUD + filtros avançados + resumo
  FuncionarioViewSet             — CRUD + folhas salariais + demissão
  MensalidadeViewSet             — CRUD + pagamento + multa + gerar em massa
  FolhaPagamentoViewSet          — CRUD + confirmar pagamento + resumo mensal
  DespesaVeiculoViewSet          — CRUD + resumo por veículo
  DespesaGeralViewSet            — CRUD + registar pagamento + pendentes
  BalancoMensalViewSet           — leitura + gerar balanço + dashboard
"""

from datetime import date

from django.db.models import Count, Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from core.permissions import (
    IsGestor,
    PodeLerMensalidade,
)
from rest_framework.response import Response

from financeiro.models import (
    BalancoMensal,
    Categoria,
    ConfiguracaoFinanceira,
    DespesaGeral,
    DespesaVeiculo,
    FolhaPagamento,
    Funcionario,
    Mensalidade,
    Transacao,
)
from financeiro.serializers import (
    BalancoMensalSerializer,
    CategoriaSerializer,
    ConfiguracaoFinanceiraSerializer,
    ConfirmarPagamentoSerializer,
    DespesaGeralSerializer,
    DespesaVeiculoSerializer,
    FolhaPagamentoSerializer,
    FolhaPagamentoWriteSerializer,
    FuncionarioSerializer,
    FuncionarioWriteSerializer,
    GerarBalancoSerializer,
    MensalidadeListSerializer,
    MensalidadeSerializer,
    MensalidadeWriteSerializer,
    PagamentoDespesaGeralSerializer,
    PagamentoSerializer,
    TransacaoSerializer,
    TransacaoWriteSerializer,
)


class ConfiguracaoFinanceiraViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):

    serializer_class = ConfiguracaoFinanceiraSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ConfiguracaoFinanceira.objects.all()

    def get_permissions(self):
        # Configuração: só gestores acedem
        return [IsGestor()]


class CategoriaViewSet(viewsets.ModelViewSet):

    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['tipo']
    search_fields = ['nome']

    def get_queryset(self):
        return Categoria.objects.all()

    def get_permissions(self):
        return [IsGestor()]


class TransacaoViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'metodo', 'categoria', 'categoria__tipo', 'aluno']
    search_fields = ['descricao', 'aluno__user__nome']
    ordering_fields = ['data_vencimento', 'valor', 'status']
    ordering = ['-data_vencimento']

    def get_queryset(self):
        return (
            Transacao.objects
            .select_related('categoria', 'aluno__user')
        )

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return TransacaoWriteSerializer
        return TransacaoSerializer

    def get_permissions(self):
        return [IsGestor()]

    def perform_destroy(self, instance):
        if instance.status == 'PAGO':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Transacções pagas não podem ser eliminadas.')
        instance.delete()

    # ── Actions ──────────────────────────────

    @action(detail=False, methods=['get'], url_path='resumo')
    def resumo(self, request):
        """
        Totais de receitas e despesas por status.
        Útil para o dashboard financeiro.
        """
        qs = self.get_queryset()

        receitas = (
            qs.filter(categoria__tipo='RECEITA')
            .values('status')
            .annotate(total=Sum('valor'), qtd=Count('id'))
        )
        despesas = (
            qs.filter(categoria__tipo='DESPESA')
            .values('status')
            .annotate(total=Sum('valor'), qtd=Count('id'))
        )
        return Response({
            'receitas': list(receitas),
            'despesas': list(despesas),
        })

    @action(detail=False, methods=['get'], url_path='em-atraso')
    def em_atraso(self, request):
        """Transacções vencidas e não pagas."""
        qs = self.get_queryset().filter(
            Q(status='ATRASADO') | Q(status='PENDENTE', data_vencimento__lt=date.today())
        )
        serializer = TransacaoSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='por-aluno')
    def por_aluno(self, request):
        """
        Receitas de um aluno específico.
        Parâmetro obrigatório: ?aluno_id=<id>
        """
        aluno_id = request.query_params.get('aluno_id')
        if not aluno_id:
            return Response(
                {'erro': 'Parâmetro aluno_id é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        qs = self.get_queryset().filter(
            aluno_id=aluno_id, categoria__tipo='RECEITA'
        )
        serializer = TransacaoSerializer(qs, many=True)
        return Response(serializer.data)


class FuncionarioViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ativo', 'user__role']
    search_fields = ['user__nome', 'user__email', 'nuit']
    ordering_fields = ['user__nome', 'data_admissao']
    ordering = ['user__nome']

    def get_queryset(self):
        return (
            Funcionario.objects
            .select_related(
                'user',
                'motorista_perfil__user',
                'monitor_perfil__user',
                'gestor_perfil__user',
            )
        )

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return FuncionarioWriteSerializer
        return FuncionarioSerializer

    def get_permissions(self):
        if self.action == 'me':
            return [IsAuthenticated()]
        # Funcionários: acesso exclusivo a gestores
        return [IsGestor()]

    def perform_destroy(self, instance):
        """Soft delete via método do modelo."""
        instance.delete()

    # ── Actions ──────────────────────────────

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Perfil financeiro do utilizador autenticado."""
        try:
            funcionario = Funcionario.objects.select_related('user').get(user=request.user)
        except Funcionario.DoesNotExist:
            return Response(
                {'erro': 'Perfil financeiro não encontrado para este utilizador.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = FuncionarioSerializer(funcionario)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='folhas')
    def folhas(self, request, pk=None):
        """Histórico de folhas salariais do funcionário."""
        funcionario = self.get_object()
        qs = funcionario.pagamentos.all().order_by('-mes_referente')
        serializer = FolhaPagamentoSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='demitir')
    def demitir(self, request, pk=None):
        """Demite o funcionário (soft delete com data de demissão)."""
        funcionario = self.get_object()
        if not funcionario.ativo:
            return Response(
                {'erro': 'O funcionário já está inactivo.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        funcionario.delete()  # soft delete do modelo
        return Response({'mensagem': f'{funcionario.user.nome} demitido com sucesso.'})


class MensalidadeViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'aluno', 'mes_referente']
    search_fields = ['aluno__user__nome', 'nr_fatura']
    ordering_fields = ['mes_referente', 'valor_base', 'estado']
    ordering = ['-mes_referente']

    def get_queryset(self):
        user = self.request.user

        qs = (
            Mensalidade.objects
            .select_related('aluno__user', 'aluno__encarregado__user')
            .prefetch_related('recibo_emitido')
        )

        # Encarregados vêem apenas as mensalidades dos seus alunos
        try:
            encarregado = user.perfil_encarregado
            return qs.filter(aluno__encarregado=encarregado)
        except Exception:
            pass

        # Alunos vêem apenas as suas próprias mensalidades
        try:
            aluno = user.perfil_aluno
            return qs.filter(aluno=aluno)
        except Exception:
            pass

        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return MensalidadeListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return MensalidadeWriteSerializer
        return MensalidadeSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update',
                           'destroy', 'gerar', 'pagar', 'aplicar_multa'):
            return [IsGestor()]
        # list, retrieve, do_mes, em_atraso, resumo_mes
        return [PodeLerMensalidade()]

    def perform_destroy(self, instance):
        if instance.estado not in ('PENDENTE', 'ATRASADO'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                'Só é possível eliminar mensalidades em estado PENDENTE ou ATRASADO.'
            )
        instance.delete()

    # ── Actions ──────────────────────────────

    @action(detail=False, methods=['get'], url_path='do-mes')
    def do_mes(self, request):
        """
        Mensalidades de um mês específico.
        Parâmetros obrigatórios: ?mes=<1-12>&ano=<YYYY>
        """
        try:
            mes = int(request.query_params.get('mes', 0))
            ano = int(request.query_params.get('ano', 0))
        except (TypeError, ValueError):
            return Response(
                {'erro': 'Parâmetros mes e ano devem ser inteiros.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not (1 <= mes <= 12) or ano < 2020:
            return Response(
                {'erro': 'Mês (1-12) ou ano inválido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        qs = self.get_queryset().filter(
            mes_referente__month=mes,
            mes_referente__year=ano,
        )
        serializer = MensalidadeListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='em-atraso')
    def em_atraso(self, request):
        """Mensalidades com estado ATRASADO."""
        qs = self.get_queryset().filter(estado='ATRASADO')
        serializer = MensalidadeListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='pagar')
    def pagar(self, request, pk=None):
        """Regista um pagamento (parcial ou total) para a mensalidade."""
        mensalidade = self.get_object()

        if mensalidade.estado in ('PAGO', 'ISENTO'):
            return Response(
                {'erro': f'Esta mensalidade já está "{mensalidade.get_estado_display()}".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PagamentoSerializer(
            data=request.data, context={'mensalidade': mensalidade}
        )
        serializer.is_valid(raise_exception=True)

        try:
            mensalidade.registrar_pagamento(
                valor=serializer.validated_data['valor'], metodo=serializer.validated_data['metodo'],
            )
        except Exception as e:
            return Response({'erro': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        mensalidade.refresh_from_db()
        return Response(
            MensalidadeSerializer(mensalidade).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='aplicar-multa')
    def aplicar_multa(self, request, pk=None):
        """Aplica a multa de atraso se aplicável."""
        mensalidade = self.get_object()
        aplicada = mensalidade.verificar_e_aplicar_multa()

        if not aplicada:
            return Response(
                {'mensagem': 'Multa não aplicável (já pago, isento, dentro do prazo ou já aplicada).'},
                status=status.HTTP_200_OK
            )

        mensalidade.refresh_from_db()
        return Response(
            MensalidadeSerializer(mensalidade).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='gerar')
    def gerar(self, request):
        """
        Gera mensalidades para todos os alunos activos sem registo
        para o mês/ano indicado.
        Payload: { "mes": 3, "ano": 2025 }
        """
        ser = GerarBalancoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        total = Mensalidade.objects.gerar_mensalidades_mes(
            ser.validated_data['mes'],
            ser.validated_data['ano'],
        )
        return Response(
            {'mensagem': f'{total} mensalidade(s) gerada(s).'},
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'], url_path='resumo-mes')
    def resumo_mes(self, request):
        """
        Contagem de mensalidades por estado para um mês.
        Parâmetros: ?mes=<1-12>&ano=<YYYY>
        """
        try:
            mes = int(request.query_params.get('mes', date.today().month))
            ano = int(request.query_params.get('ano', date.today().year))
        except (TypeError, ValueError):
            return Response({'erro': 'Parâmetros inválidos.'}, status=status.HTTP_400_BAD_REQUEST)

        resumo = Mensalidade.objects.resumo_estatistico(mes, ano)
        total_devedor = Mensalidade.objects.total_devedor_mes(mes, ano)

        return Response({
            'mes': f'{mes:02d}/{ano}',
            'por_estado': list(resumo),
            'total_devedor': total_devedor,
        })


class FolhaPagamentoViewSet(viewsets.ModelViewSet):

    permission_classes = [IsGestor]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'funcionario', 'mes_referente']
    ordering = ['-mes_referente']

    def get_queryset(self):
        return (
            FolhaPagamento.objects
            .select_related('funcionario__user', 'transacao_vinculada__categoria')
        )

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return FolhaPagamentoWriteSerializer
        return FolhaPagamentoSerializer

    def perform_destroy(self, instance):
        if instance.status == 'PAGO':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Folhas já pagas não podem ser eliminadas.')
        instance.delete()

    # ── Actions ──────────────────────────────

    @action(detail=True, methods=['post'], url_path='confirmar')
    def confirmar(self, request, pk=None):
        """Confirma o pagamento de uma folha salarial e gera a transacção."""
        folha = self.get_object()

        if folha.status == 'PAGO':
            return Response(
                {'erro': 'Esta folha já foi paga.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ser = ConfirmarPagamentoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        folha.confirmar_pagamento(metodo=ser.validated_data['metodo'])
        folha.refresh_from_db()
        return Response(FolhaPagamentoSerializer(folha).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='resumo-mes')
    def resumo_mes(self, request):
        """Totais da folha salarial para um mês."""
        try:
            mes = int(request.query_params.get('mes', date.today().month))
            ano = int(request.query_params.get('ano', date.today().year))
        except (TypeError, ValueError):
            return Response({'erro': 'Parâmetros inválidos.'}, status=status.HTTP_400_BAD_REQUEST)

        qs = self.get_queryset().filter(
            mes_referente__month=mes, mes_referente__year=ano
        )
        totais = qs.aggregate(
            total_pago=Sum('valor_total', filter=Q(status='PAGO')),
            total_pendente=Sum('valor_total', filter=Q(status='PENDENTE')),
            qtd_pago=Count('id', filter=Q(status='PAGO')),
            qtd_pendente=Count('id', filter=Q(status='PENDENTE')),
        )
        return Response({
            'mes': f'{mes:02d}/{ano}',
            'total_pago': totais['total_pago'] or 0,
            'total_pendente': totais['total_pendente'] or 0,
            'qtd_pago': totais['qtd_pago'],
            'qtd_pendente': totais['qtd_pendente'],
        })

    @action(detail=False, methods=['get'], url_path='pendentes')
    def pendentes(self, request):
        """Folhas salariais ainda não pagas."""
        qs = self.get_queryset().filter(status='PENDENTE')
        serializer = FolhaPagamentoSerializer(qs, many=True)
        return Response(serializer.data)


class DespesaVeiculoViewSet(viewsets.ModelViewSet):

    serializer_class = DespesaVeiculoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['veiculo', 'tipo', 'data']
    ordering = ['-data']

    def get_queryset(self):
        return (
            DespesaVeiculo.objects
            .select_related('veiculo__motorista__user', 'transacao__categoria')
        )

    def get_permissions(self):
        # DespesaVeiculo criada automaticamente por signal — só gestor acede
        return [IsGestor()]

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied(
            'Despesas da frota não podem ser eliminadas. Utilize um estorno.'
        )

    # ── Actions ──────────────────────────────

    @action(detail=False, methods=['get'], url_path='resumo-frota')
    def resumo_frota(self, request):
        """Totais de despesa por veículo e por tipo."""
        resumo = (
            self.get_queryset()
            .values('veiculo__matricula', 'tipo')
            .annotate(total=Sum('valor'), qtd=Count('id'))
            .order_by('veiculo__matricula', 'tipo')
        )
        return Response(list(resumo))


class DespesaGeralViewSet(viewsets.ModelViewSet):

    serializer_class = DespesaGeralSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['pago', 'categoria', 'data_vencimento']
    search_fields = ['descricao']
    ordering = ['-data_vencimento']

    def get_queryset(self):
        return (
            DespesaGeral.objects
            .select_related('categoria', 'transacao__categoria')
        )

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'pagar'):
            return [IsGestor()]
        return [IsGestor()]

    # ── Actions ──────────────────────────────

    @action(detail=True, methods=['post'], url_path='pagar')
    def pagar(self, request, pk=None):
        """Regista o pagamento de uma despesa geral."""
        despesa = self.get_object()

        if despesa.pago:
            return Response(
                {'erro': 'Esta despesa já foi paga.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ser = PagamentoDespesaGeralSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        despesa.registrar_pagamento(metodo=ser.validated_data['metodo'])
        despesa.refresh_from_db()
        return Response(DespesaGeralSerializer(despesa).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='pendentes')
    def pendentes(self, request):
        """Despesas ainda não pagas."""
        qs = self.get_queryset().filter(pago=False)
        serializer = DespesaGeralSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='resumo')
    def resumo(self, request):
        """Totais de despesas pagas e pendentes por categoria."""
        resumo = (
            self.get_queryset()
            .values('categoria__nome', 'pago')
            .annotate(total=Sum('valor'), qtd=Count('id'))
            .order_by('categoria__nome')
        )
        return Response(list(resumo))


class BalancoMensalViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):

    serializer_class = BalancoMensalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['finalizado']
    ordering = ['-mes_referencia']

    def get_queryset(self):
        return BalancoMensal.objects.select_related('transacao__categoria')

    def get_permissions(self):
        if self.action == 'gerar':
            return [IsGestor()]
        # list, retrieve, dashboard
        return [IsGestor()]

    # ── Actions ──────────────────────────────

    @action(detail=False, methods=['post'], url_path='gerar')
    def gerar(self, request):
        """
        Calcula e persiste o balanço para o mês indicado.
        Payload: { "mes": 3, "ano": 2025 }
        """
        ser = GerarBalancoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        balanco = BalancoMensal.gerar_balanco(
            ser.validated_data['mes'], ser.validated_data['ano'],
        )
        return Response(
            BalancoMensalSerializer(balanco).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        """
        Métricas rápidas para o painel principal:
        - Balanço do mês actual (ou último fechado)
        - Mensalidades em atraso
        - Despesas pendentes
        - Folhas salariais por pagar
        """
        hoje = date.today()

        # Balanço mais recente
        ultimo_balanco = self.get_queryset().first()
        balanco_data = (
            BalancoMensalSerializer(ultimo_balanco).data
            if ultimo_balanco else None
        )

        # Mensalidades em atraso
        from financeiro.models import Mensalidade
        mensalidades_atraso = Mensalidade.objects.filter(estado='ATRASADO').count()
        total_devedor = Mensalidade.objects.total_devedor_mes(hoje.month, hoje.year)

        # Despesas pendentes
        despesas_pendentes = DespesaGeral.objects.filter(pago=False).aggregate(
            total=Sum('valor'), qtd=Count('id')
        )

        # Folhas por pagar
        folhas_pendentes = FolhaPagamento.objects.filter(status='PENDENTE').aggregate(
            total=Sum('valor_total'), qtd=Count('id')
        )

        return Response({
            'ultimo_balanco': balanco_data,
            'mensalidades_em_atraso': mensalidades_atraso,
            'total_devedor_mes_atual': total_devedor,
            'despesas_gerais_pendentes': {
                'total': despesas_pendentes['total'] or 0,
                'qtd': despesas_pendentes['qtd'],
            },
            'folhas_salariais_pendentes': {
                'total': folhas_pendentes['total'] or 0,
                'qtd': folhas_pendentes['qtd'],
            },
        })
