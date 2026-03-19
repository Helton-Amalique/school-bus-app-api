"""
transporte/filters.py
=====================
FilterSets customizados para o módulo transporte.

Permitem filtragem por intervalos de datas nos endpoints:
  - TransporteAluno  → ?data_min=2025-01-01&data_max=2025-01-31
  - Manutencao       → ?data_inicio_min=... &data_inicio_max=...
  - Abastecimento    → ?data_min=2025-01-01&data_max=2025-01-31
"""

import django_filters

from transporte.models import Abastecimento, Manutencao, TransporteAluno


class TransporteAlunoFilter(django_filters.FilterSet):
    """
    Filtros avançados para registos de transporte.

    Exemplos:
      ?status=EMBARCADO
      ?data_min=2025-03-01&data_max=2025-03-31
      ?rota=1&aluno=2
    """

    data_min = django_filters.DateFilter(field_name='data', lookup_expr='gte',
                                         label='Data a partir de (YYYY-MM-DD)')
    data_max = django_filters.DateFilter(field_name='data', lookup_expr='lte',
                                         label='Data até (YYYY-MM-DD)')

    class Meta:
        model = TransporteAluno
        fields = ['status', 'rota', 'aluno', 'data_min', 'data_max']


class ManutencaoFilter(django_filters.FilterSet):
    """
    Filtros avançados para manutenções.

    Exemplos:
      ?concluida=true
      ?data_inicio_min=2025-01-01&data_inicio_max=2025-06-30
      ?tipo=PREVENTIVA
    """

    data_inicio_min = django_filters.DateFilter(
        field_name='data_inicio', lookup_expr='gte',
        label='Data início a partir de (YYYY-MM-DD)'
    )
    data_inicio_max = django_filters.DateFilter(
        field_name='data_inicio', lookup_expr='lte',
        label='Data início até (YYYY-MM-DD)'
    )

    class Meta:
        model = Manutencao
        fields = ['concluida', 'tipo', 'veiculo', 'data_inicio_min', 'data_inicio_max']


class AbastecimentoFilter(django_filters.FilterSet):
    """
    Filtros avançados para abastecimentos.

    Exemplos:
      ?veiculo=1
      ?data_min=2025-03-01&data_max=2025-03-31
      ?posto_combustivel=Puma
    """

    data_min = django_filters.DateFilter(field_name='data', lookup_expr='gte',
                                         label='Data a partir de (YYYY-MM-DD)')
    data_max = django_filters.DateFilter(field_name='data', lookup_expr='lte',
                                         label='Data até (YYYY-MM-DD)')

    class Meta:
        model = Abastecimento
        fields = ['veiculo', 'posto_combustivel', 'data_min', 'data_max']
