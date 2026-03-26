"""
financeiro/serializers.py
=========================
Serializers DRF para o módulo financeiro.

Serializers:
  ConfiguracaoFinanceiraSerializer   — leitura/edição do singleton
  CategoriaSerializer                — CRUD de categorias
  TransacaoSerializer                — leitura de transacções
  TransacaoWriteSerializer           — criação/edição de transacções
  FuncionarioSerializer              — leitura de funcionário
  FuncionarioWriteSerializer         — criação/edição
  MensalidadeSerializer              — leitura completa
  MensalidadeListSerializer          — listagem leve
  PagamentoSerializer                — payload para registar pagamento
  FolhaPagamentoSerializer           — leitura de folha salarial
  FolhaPagamentoWriteSerializer      — criação de folha salarial
  ConfirmarPagamentoSerializer       — payload para confirmar folha
  DespesaVeiculoSerializer           — leitura/criação de despesas de frota
  DespesaGeralSerializer             — leitura/criação de despesas gerais
  PagamentoDespesaGeralSerializer    — payload para pagar despesa geral
  BalancoMensalSerializer            — leitura de balanço mensal
  GerarBalancoSerializer             — payload para gerar balanço
"""

from datetime import date
from decimal import Decimal

from rest_framework import serializers

from financeiro.models import (
    BalancoMensal,
    Categoria,
    ConfiguracaoFinanceira,
    DespesaGeral,
    DespesaVeiculo,
    FolhaPagamento,
    Funcionario,
    Mensalidade,
    Recibo,
    Transacao,
)


# ──────────────────────────────────────────────
# CONFIGURAÇÃO FINANCEIRA
# ──────────────────────────────────────────────

class ConfiguracaoFinanceiraSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracaoFinanceira
        fields = ('id', 'dia_vencimento', 'dia_limite_pagamento', 'valor_multa_fixa')


# ──────────────────────────────────────────────
# CATEGORIA
# ──────────────────────────────────────────────

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ('id', 'nome', 'tipo')

    def validate(self, data):
        nome = data.get('nome', getattr(self.instance, 'nome', None))
        tipo = data.get('tipo', getattr(self.instance, 'tipo', None))
        qs = Categoria.objects.filter(nome=nome, tipo=tipo)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f'Já existe uma categoria "{nome}" do tipo {tipo}.'
            )
        return data


# ──────────────────────────────────────────────
# TRANSACAO
# ──────────────────────────────────────────────

class TransacaoSerializer(serializers.ModelSerializer):
    """Leitura completa de uma transacção."""

    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)
    tipo = serializers.CharField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    aluno_nome = serializers.SerializerMethodField()

    class Meta:
        model = Transacao
        fields = (
            'id', 'descricao', 'valor', 'categoria', 'categoria_nome', 'tipo', 'metodo', 'status', 'is_overdue', 'data_vencimento', 'data_pagamento', 'aluno', 'aluno_nome', 'referencia_externa_id',
        )

    def get_aluno_nome(self, obj):
        return obj.aluno.user.nome if obj.aluno else None


class TransacaoWriteSerializer(serializers.ModelSerializer):
    """Criação/edição manual de transacções."""

    class Meta:
        model  = Transacao
        fields = (
            'descricao', 'valor', 'categoria',
            'metodo', 'status',
            'data_vencimento', 'data_pagamento',
            'aluno', 'referencia_externa_id',
        )

    def validate(self, data):
        categoria = data.get('categoria', getattr(self.instance, 'categoria', None))
        aluno = data.get('aluno', getattr(self.instance, 'aluno', None))
        if categoria and categoria.tipo == 'DESPESA' and aluno:
            raise serializers.ValidationError(
                {'aluno': 'Despesas não podem estar associadas a alunos.'}
            )

        # Impede alteração de valor em transacção já paga
        if self.instance and self.instance.status == 'PAGO':
            novo_valor = data.get('valor')
            if novo_valor and novo_valor != self.instance.valor:
                raise serializers.ValidationError(
                    {'valor': 'Não é permitido alterar o valor de uma transacção já paga.'}
                )
        return data


# ──────────────────────────────────────────────
# FUNCIONARIO
# ──────────────────────────────────────────────

class FuncionarioSerializer(serializers.ModelSerializer):
    """Leitura completa de funcionário."""

    nome = serializers.CharField(source='user.nome', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)
    role_display = serializers.CharField(source='user.get_role_display', read_only=True)
    salario_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Funcionario
        fields = (
            'id', 'user', 'nome', 'email', 'role', 'role_display',
            'nuit', 'salario_base', 'subsidio_transporte', 'salario_total',
            'ativo', 'data_admissao', 'data_demissao',
            'motorista_perfil', 'monitor_perfil', 'gestor_perfil',
        )
        read_only_fields = ('data_admissao', 'data_demissao', 'salario_total')


class FuncionarioWriteSerializer(serializers.ModelSerializer):
    """Criação/edição de funcionário."""

    class Meta:
        model = Funcionario
        fields = (
            'user', 'nuit', 'salario_base', 'subsidio_transporte', 'ativo', 'motorista_perfil', 'monitor_perfil', 'gestor_perfil',
        )

    def validate_nuit(self, value):
        if not value.isdigit() or len(value) != 9:
            raise serializers.ValidationError('O NUIT deve conter exactamente 9 dígitos numéricos.')
        return value

    def validate(self, data):
        user = data.get('user', getattr(self.instance, 'user', None))
        if not user:
            return data

        PERFIL_POR_ROLE = {
            'MOTORISTA': 'motorista_perfil',
            'MONITOR': 'monitor_perfil',
            'GESTOR': 'gestor_perfil',
        }
        TODOS = list(PERFIL_POR_ROLE.values())

        perfis_preenchidos = [c for c in TODOS if data.get(c)]
        if len(perfis_preenchidos) > 1:
            raise serializers.ValidationError(
                'Apenas um perfil de core pode estar preenchido.'
            )

        role = user.role
        if role in PERFIL_POR_ROLE:
            campo = PERFIL_POR_ROLE[role]
            if not data.get(campo):
                raise serializers.ValidationError({
                    campo: f'Obrigatório para o role {role}.'
                })
        elif perfis_preenchidos:
            raise serializers.ValidationError(
                f'Utilizadores com role {role} não têm perfil de core associado.'
            )
        return data


# ──────────────────────────────────────────────
# MENSALIDADE
# ──────────────────────────────────────────────

class ReciboSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recibo
        fields = ('id', 'codigo_recibo', 'arquivo', 'data_emissao')
        read_only_fields = fields


class MensalidadeSerializer(serializers.ModelSerializer):
    """Leitura completa de mensalidade."""

    aluno_nome = serializers.CharField(source='aluno.user.nome', read_only=True)
    mes_display = serializers.SerializerMethodField()
    valor_total_devido = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    saldo_devedor = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    recibo = ReciboSerializer(source='recibo_emitido', read_only=True)

    class Meta:
        model  = Mensalidade
        fields = (
            'id', 'aluno', 'aluno_nome',
            'mes_referente', 'mes_display', 'nr_fatura',
            'valor_base', 'multa_atraso', 'desconto',
            'valor_total_devido', 'valor_pago_acumulado', 'saldo_devedor',
            'data_ultimo_pagamento',
            'estado', 'estado_display', 'obs',
            'recibo',
        )
        read_only_fields = (
            'nr_fatura', 'valor_total_devido', 'saldo_devedor',
            'data_ultimo_pagamento', 'recibo',
        )

    def get_mes_display(self, obj):
        return obj.mes_referente.strftime('%m/%Y')


class MensalidadeListSerializer(serializers.ModelSerializer):
    """Versão leve para listagens."""

    aluno_nome = serializers.CharField(source='aluno.user.nome', read_only=True)
    mes_display = serializers.SerializerMethodField()
    saldo_devedor = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model  = Mensalidade
        fields = (
            'id', 'aluno', 'aluno_nome',
            'mes_referente', 'mes_display',
            'nr_fatura', 'valor_base', 'saldo_devedor', 'estado',
        )

    def get_mes_display(self, obj):
        return obj.mes_referente.strftime('%m/%Y')


class PagamentoSerializer(serializers.Serializer):
    """Payload para registar um pagamento (parcial ou total) de mensalidade."""

    valor  = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        min_value=Decimal('0.01'),
    )
    metodo = serializers.ChoiceField(choices=Transacao.METODO_PAGAMENTO)

    def validate_valor(self, value):
        # Garante que não paga mais do que o saldo em dívida
        mensalidade = self.context.get('mensalidade')
        if mensalidade and value > mensalidade.saldo_devedor:
            raise serializers.ValidationError(
                f'O valor ({value} MT) excede o saldo devedor ({mensalidade.saldo_devedor} MT).'
            )
        return value


class MensalidadeWriteSerializer(serializers.ModelSerializer):
    """Criação e ajuste manual de mensalidade (admin)."""

    class Meta:
        model  = Mensalidade
        fields = (
            'aluno', 'mes_referente',
            'valor_base', 'multa_atraso', 'desconto',
            'estado', 'obs',
        )

    def validate_mes_referente(self, value):
        """
        Normaliza sempre para o primeiro dia do mês.
        Evita surpresas: o cliente envia 2025-03-15, guarda 2025-03-01.
        """
        return value.replace(day=1)

    def validate(self, data):
        aluno = data.get('aluno', getattr(self.instance, 'aluno', None))
        mes_referente = data.get('mes_referente', getattr(self.instance, 'mes_referente', None))
        pk = self.instance.pk if self.instance else None

        if aluno and mes_referente:
            qs = Mensalidade.objects.filter(
                aluno=aluno,
                mes_referente__month=mes_referente.month,
                mes_referente__year=mes_referente.year,
            )
            if pk:
                qs = qs.exclude(pk=pk)
            if qs.exists():
                raise serializers.ValidationError(
                    f'Já existe mensalidade para {aluno} em {mes_referente.strftime("%m/%Y")}.'
                )
        return data


# ──────────────────────────────────────────────
# FOLHA DE PAGAMENTO
# ──────────────────────────────────────────────

class FolhaPagamentoSerializer(serializers.ModelSerializer):
    """Leitura de folha salarial."""

    funcionario_nome = serializers.CharField(source='funcionario.user.nome', read_only=True)
    mes_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    transacao_info = TransacaoSerializer(source='transacao_vinculada', read_only=True)

    class Meta:
        model  = FolhaPagamento
        fields = (
            'id', 'funcionario', 'funcionario_nome',
            'mes_referente', 'mes_display',
            'valor_total', 'status', 'status_display',
            'data_processamento', 'transacao_info',
        )
        read_only_fields = ('data_processamento', 'transacao_info')

    def get_mes_display(self, obj):
        return obj.mes_referente.strftime('%m/%Y')


class FolhaPagamentoWriteSerializer(serializers.ModelSerializer):
    """Criação de folha salarial."""

    class Meta:
        model  = FolhaPagamento
        fields = ('funcionario', 'mes_referente', 'valor_total')

    def validate_mes_referente(self, value):
        """Normaliza para o primeiro dia do mês."""
        return value.replace(day=1)

    def validate(self, data):
        funcionario = data.get('funcionario', getattr(self.instance, 'funcionario', None))
        mes_referente = data.get('mes_referente', getattr(self.instance, 'mes_referente', None))
        pk = self.instance.pk if self.instance else None

        if funcionario and mes_referente:
            qs = FolhaPagamento.objects.filter(
                funcionario=funcionario,
                mes_referente__month=mes_referente.month,
                mes_referente__year=mes_referente.year,
            )
            if pk:
                qs = qs.exclude(pk=pk)
            if qs.exists():
                raise serializers.ValidationError(
                    f'Já existe folha para {funcionario} em {mes_referente.strftime("%m/%Y")}.'
                )
        return data


class ConfirmarPagamentoSerializer(serializers.Serializer):
    """Payload para confirmar pagamento de uma folha salarial."""

    metodo = serializers.ChoiceField(
        choices=Transacao.METODO_PAGAMENTO,
        default='TRANSFERENCIA'
    )


# ──────────────────────────────────────────────
# DESPESA VEÍCULO
# ──────────────────────────────────────────────

class DespesaVeiculoSerializer(serializers.ModelSerializer):
    """Leitura e criação de despesas de frota."""

    veiculo_matricula = serializers.CharField(source='veiculo.matricula', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    transacao_info = TransacaoSerializer(source='transacao', read_only=True)

    class Meta:
        model  = DespesaVeiculo
        fields = (
            'id', 'veiculo', 'veiculo_matricula', 'tipo', 'tipo_display', 'valor', 'data', 'km_atual', 'transacao', 'transacao_info',
        )
        read_only_fields = ('transacao', 'transacao_info')

    def validate(self, data):
        # Impede edição de valor em despesa existente
        if self.instance:
            novo_valor = data.get('valor')
            if novo_valor and novo_valor != self.instance.valor:
                raise serializers.ValidationError(
                    {'valor': 'Não é permitido alterar o valor de uma despesa já registada.'}
                )
        return data


# ──────────────────────────────────────────────
# DESPESA GERAL
# ──────────────────────────────────────────────

class DespesaGeralSerializer(serializers.ModelSerializer):
    """Leitura e criação de despesas gerais."""

    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)
    transacao_info = TransacaoSerializer(source='transacao', read_only=True)

    class Meta:
        model = DespesaGeral
        fields = (
            'id', 'descricao', 'valor', 'data_vencimento', 'pago', 'categoria', 'categoria_nome', 'transacao', 'transacao_info',
        )
        read_only_fields = ('pago', 'transacao', 'transacao_info')

    def validate(self, data):
        if self.instance and self.instance.pago:
            novo_valor = data.get('valor')
            if novo_valor and novo_valor != self.instance.valor:
                raise serializers.ValidationError(
                    {'valor': 'Não é permitido alterar o valor de uma despesa já paga.'}
                )
        return data


class PagamentoDespesaGeralSerializer(serializers.Serializer):
    """Payload para registar pagamento de uma despesa geral."""

    metodo = serializers.ChoiceField(
        choices=Transacao.METODO_PAGAMENTO,
        default='DINHEIRO'
    )


# ──────────────────────────────────────────────
# BALANÇO MENSAL
# ──────────────────────────────────────────────

class BalancoMensalSerializer(serializers.ModelSerializer):
    """Leitura de balanço mensal com totais e resultado."""

    mes_display = serializers.SerializerMethodField()
    total_despesas = serializers.SerializerMethodField()
    resultado_display = serializers.SerializerMethodField()
    transacao_info = TransacaoSerializer(source='transacao', read_only=True)

    class Meta:
        model  = BalancoMensal
        fields = (
            'id', 'mes_referencia', 'mes_display', 'data_fecho',
            'total_receitas_previstas', 'total_receitas_pagas',
            'total_despesas_gerais', 'total_despesas_frota', 'total_folha_salarial',
            'total_despesas', 'lucro_prejuizo', 'resultado_display',
            'finalizado', 'transacao_info',
        )
        read_only_fields = fields

    def get_mes_display(self, obj):
        return obj.mes_referencia.strftime('%m/%Y')

    def get_total_despesas(self, obj):
        return obj.total_despesas_gerais + obj.total_despesas_frota + obj.total_folha_salarial

    def get_resultado_display(self, obj):
        sinal = '+' if obj.lucro_prejuizo >= 0 else ''
        return f"{sinal}{obj.lucro_prejuizo} MT"


class GerarBalancoSerializer(serializers.Serializer):
    """Payload para solicitar o cálculo de um balanço mensal."""

    mes = serializers.IntegerField(min_value=1, max_value=12)
    ano = serializers.IntegerField(min_value=2020, max_value=2100)

    def validate(self, data):
        # Não permitir gerar balanço para um mês futuro
        hoje = date.today()
        if (data['ano'], data['mes']) > (hoje.year, hoje.month):
            raise serializers.ValidationError(
                'Não é possível gerar balanço para um mês futuro.'
            )
        return data
