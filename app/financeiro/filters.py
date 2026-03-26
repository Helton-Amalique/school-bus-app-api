"""
financeiro/filters.py
=====================
FilterSets customizados para o módulo financeiro.

Permitem filtragem por intervalos de datas nos endpoints:
  - Transacao      → ?data_vencimento_min=...&data_vencimento_max=...
  - Mensalidade    → ?mes_referente_min=...&mes_referente_max=...
  - DespesaVeiculo → ?data_min=...&data_max=...
  - DespesaGeral   → ?data_vencimento_min=...&data_vencimento_max=...
  - FolhaPagamento → ?mes_referente_min=...&mes_referente_max=...
"""

import django_filters

from financeiro.models import (
    DespesaGeral,
    DespesaVeiculo,
    FolhaPagamento,
    Mensalidade,
    Transacao,
)


class TransacaoFilter(django_filters.FilterSet):
    """
    Filtros avançados para transacções.

    Exemplos:
      ?status=PAGO&categoria__tipo=RECEITA
      ?data_vencimento_min=2025-01-01&data_vencimento_max=2025-03-31
      ?valor_min=1000&valor_max=5000
    """

    data_vencimento_min = django_filters.DateFilter(
        field_name='data_vencimento', lookup_expr='gte',
        label='Vencimento a partir de'
    )
    data_vencimento_max = django_filters.DateFilter(
        field_name='data_vencimento', lookup_expr='lte',
        label='Vencimento até'
    )
    data_pagamento_min = django_filters.DateFilter(
        field_name='data_pagamento', lookup_expr='gte',
        label='Pagamento a partir de'
    )
    data_pagamento_max = django_filters.DateFilter(
        field_name='data_pagamento', lookup_expr='lte',
        label='Pagamento até'
    )
    valor_min = django_filters.NumberFilter(field_name='valor', lookup_expr='gte')
    valor_max = django_filters.NumberFilter(field_name='valor', lookup_expr='lte')

    class Meta:
        model = Transacao
        fields = [
            'status', 'metodo', 'categoria', 'categoria__tipo', 'aluno',
            'data_vencimento_min', 'data_vencimento_max',
            'data_pagamento_min', 'data_pagamento_max',
            'valor_min', 'valor_max',
        ]


class MensalidadeFilter(django_filters.FilterSet):
    """
    Filtros avançados para mensalidades.

    Exemplos:
      ?estado=ATRASADO&aluno=3
      ?mes_referente_min=2025-01-01&mes_referente_max=2025-06-01
    """

    mes_referente_min = django_filters.DateFilter(
        field_name='mes_referente', lookup_expr='gte',
        label='Mês a partir de (YYYY-MM-01)'
    )
    mes_referente_max = django_filters.DateFilter(
        field_name='mes_referente', lookup_expr='lte',
        label='Mês até (YYYY-MM-01)'
    )

    class Meta:
        model = Mensalidade
        fields = ['estado', 'aluno', 'mes_referente_min', 'mes_referente_max']


class DespesaVeiculoFilter(django_filters.FilterSet):
    """
    Filtros avançados para despesas de frota.

    Exemplos:
      ?veiculo=1&tipo=COMBUSTIVEL
      ?data_min=2025-01-01&data_max=2025-12-31
    """

    data_min = django_filters.DateFilter(field_name='data', lookup_expr='gte')
    data_max = django_filters.DateFilter(field_name='data', lookup_expr='lte')

    class Meta:
        model = DespesaVeiculo
        fields = ['veiculo', 'tipo', 'data_min', 'data_max']


class DespesaGeralFilter(django_filters.FilterSet):
    """
    Filtros avançados para despesas gerais.

    Exemplos:
      ?pago=false
      ?data_vencimento_min=2025-01-01&data_vencimento_max=2025-03-31
    """

    data_vencimento_min = django_filters.DateFilter(
        field_name='data_vencimento', lookup_expr='gte'
    )
    data_vencimento_max = django_filters.DateFilter(
        field_name='data_vencimento', lookup_expr='lte'
    )

    class Meta:
        model = DespesaGeral
        fields = ['pago', 'categoria', 'data_vencimento_min', 'data_vencimento_max']


class FolhaPagamentoFilter(django_filters.FilterSet):
    """
    Filtros avançados para folhas salariais.

    Exemplos:
      ?status=PENDENTE&funcionario=2
      ?mes_referente_min=2025-01-01&mes_referente_max=2025-06-01
    """

    mes_referente_min = django_filters.DateFilter(
        field_name='mes_referente', lookup_expr='gte'
    )
    mes_referente_max = django_filters.DateFilter(
        field_name='mes_referente', lookup_expr='lte'
    )

    class Meta:
        model = FolhaPagamento
        fields = ['status', 'funcionario', 'mes_referente_min', 'mes_referente_max']
