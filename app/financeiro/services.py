from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from core.models import Aluno
from financeiro.models import (
    ConfiguracaoFinanceira,
    FolhaPagamento,
    Funcionario,
    LogNotificacoes,
    Mensalidade,
)


# =============================================================================
# NOTIFICAÇÕES
# =============================================================================

def enviar_notificacao_multa(mensalidade):
    """
    Envia SMS e/ou Email ao encarregado informando sobre a multa aplicada.
    Regista o resultado em LogNotificacoes.
    """
    encarregado = mensalidade.aluno.encarregado
    nome_aluno = mensalidade.aluno.user.nome
    mes = mensalidade.mes_referente.strftime("%m/%Y")
    novo_total = mensalidade.valor_total_devido

    mensagem = (
        f"Transporte Escolar: Foi aplicada uma multa de "
        f"{mensalidade.multa_atraso} MT à mensalidade de {mes} "
        f"do aluno {nome_aluno}. "
        f"Novo total: {novo_total} MT. Evite cortes no serviço."
    )

    # Envio de SMS
    if encarregado.telefone:
        sucesso_sms = True
        resposta_sms = ""
        try:
            print(f"[SMS] → {encarregado.telefone}: {mensagem}")
        except Exception as e:
            sucesso_sms = False
            resposta_sms = str(e)

        LogNotificacoes.objects.create(
            mensalidade=mensalidade,
            tipo='SMS',
            destino=encarregado.telefone,
            sucesso=sucesso_sms,
            resposta_server=resposta_sms,
        )

    # Envio de Email
    if encarregado.user.email:
        sucesso_email = True
        resposta_email = ""
        try:
            print(f"[EMAIL] → {encarregado.user.email}: {mensagem}")
        except Exception as e:
            sucesso_email = False
            resposta_email = str(e)

        LogNotificacoes.objects.create(
            mensalidade=mensalidade,
            tipo='EMAIL',
            destino=encarregado.user.email,
            sucesso=sucesso_email,
            resposta_server=resposta_email,
        )


# =============================================================================
# FOLHA SALARIAL
# =============================================================================

def gerar_folha_mensal(mes, ano):
    """
    Gera rascunhos de FolhaPagamento para todos os funcionários ativos
    que ainda não têm folha para o mês/ano indicado.

    OPTIMIZADO:
      - transaction.atomic() para garantir consistência
      - bulk_create para melhor performance com muitos funcionários
      - select_related para evitar N+1 queries no loop
    """
    primeiro_dia_mes = date(ano, mes, 1)

    funcionarios = Funcionario.objects.filter(ativo=True).select_related('user')

    ja_tem_folha = set(
        FolhaPagamento.objects
        .filter(mes_referente=primeiro_dia_mes)
        .values_list('funcionario_id', flat=True)
    )

    novas_folhas = []
    for f in funcionarios:
        if f.id not in ja_tem_folha:
            novas_folhas.append(
                FolhaPagamento(
                    funcionario=f,
                    mes_referente=primeiro_dia_mes,
                    valor_total=f.salario_total,
                    status='PENDENTE',
                )
            )

    with transaction.atomic():
        if novas_folhas:
            FolhaPagamento.objects.bulk_create(novas_folhas)
    return len(novas_folhas)

# =============================================================================
# MENSALIDADES
# =============================================================================

def gerar_mensalidade_mes(mes, ano):
    """
    Gera mensalidades para todos os alunos ativos que ainda não têm
    registo para o mês/ano solicitado."""

    return Mensalidade.objects.gerar_mensalidades_mes(mes, ano)


# =============================================================================
# MULTAS
# =============================================================================

def aplicar_multas_mensais(mes, ano):
    """
    Verifica e aplica multas a todas as mensalidades pendentes/atrasadas
    do mês indicado que já passaram do dia limite.
    """
    mensalidades = (
        Mensalidade.objects
        .filter(
            mes_referente__month=mes,
            mes_referente__year=ano,
        )
        .exclude(estado__in=['PAGO', 'ISENTO'])
        .select_related('aluno__user', 'aluno__encarregado__user')
    )

    aplicadas = 0
    for mensalidade in mensalidades:
        multa_aplicada = mensalidade.verificar_e_aplicar_multa()
        if multa_aplicada:
            aplicadas += 1
            try:
                enviar_notificacao_multa(mensalidade)
            except Exception as e:
                print(f"[AVISO] Falha ao notificar mensalidade {mensalidade.pk}: {e}")
    return aplicadas

# =============================================================================
# RELATÓRIO DE ESTADO MENSAL
# =============================================================================

def resumo_financeiro_mes(mes, ano):
    """
    Retorna um dicionário com o resumo financeiro do mês:
    total previsto, total recebido, total em dívida e total de multas aplicadas.

    OPTIMIZADO: uma única query agregada em vez de múltiplas contagens separadas
    """
    from django.db.models import Sum, Count, Q
    from decimal import Decimal

    resultado = Mensalidade.objects.filter(
        mes_referente__month=mes,
        mes_referente__year=ano,
    ).aggregate(
        total_previsto=Sum('valor_base'),
        total_recebido=Sum('valor_pago_acumulado'),
        total_multas=Sum('multa_atraso'),
        total_descontos=Sum('desconto'),
        qtd_pagas=Count('id', filter=Q(estado='PAGO')),
        qtd_pendentes=Count('id', filter=Q(estado='PENDENTE')),
        qtd_atrasadas=Count('id', filter=Q(estado='ATRASADO')),
        qtd_isentas=Count('id', filter=Q(estado='ISENTO')),
        qtd_parciais=Count('id', filter=Q(estado='PAGO_PARCIAL')),
    )

    for chave in resultado:
        if resultado[chave] is None:
            resultado[chave] = Decimal('0.00') if 'total' in chave else 0

    total_divida = (
        (resultado['total_previsto'] + resultado['total_multas']) - resultado['total_descontos'] - resultado['total_recebido']
    )
    resultado['total_divida'] = max(total_divida, Decimal('0.00'))

    return resultado
