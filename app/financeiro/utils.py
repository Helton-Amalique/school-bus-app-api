from datetime import date
from decimal import Decimal
from django.db.models import Sum
from financeiro.models import Transacao, Mensalidade


class FinanceiroService:
    @staticmethod
    def obter_resumo_mes(mes=None, ano=None):
        hoje = date.today()
        mes = mes or hoje.month
        ano = ano or hoje.year

        # 1. Total de Receitas (Mensalidades pagas no mês)
        # Filtramos transações de RECEITA com status PAGO
        receitas = Transacao.objects.filter(
            categoria__tipo='RECEITA',
            status='PAGO',
            data_pagamento__month=mes,
            data_pagamento__year=ano
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        # 2. Total de Despesas (Folhas de Pagamento confirmadas no mês)
        despesas = Transacao.objects.filter(
            categoria__tipo='DESPESA',
            status='PAGO',
            data_pagamento__month=mes,
            data_pagamento__year=ano
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        # 3. Previsão de Receita (O que ainda está PENDENTE ou ATRASADO)
        # Útil para saber quanto dinheiro ainda deve entrar
        previsao_entrada = Mensalidade.objects.filter(
            mes_referente__month=mes,
            mes_referente__year=ano
        ).exclude(estado='PAGO').aggregate(
            total=Sum('valor_base')
        )['total'] or Decimal('0.00')

        saldo_atual = receitas - despesas

        return {
            'mes': mes,
            'ano': ano,
            'receitas': receitas,
            'despesas': despesas,
            'saldo_atual': saldo_atual,
            'previsao_pendente': previsao_entrada,
            'lucro_esperado': (receitas + previsao_entrada) - despesas
        }
