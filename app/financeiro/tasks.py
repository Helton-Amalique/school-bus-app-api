"""
financeiro/tasks.py
===================
Tasks Celery do módulo financeiro.

Tasks assíncronas (chamadas via .delay() ou .apply_async()):
  - gerar_pdf_recibo_task            → gera PDF após pagamento completo
  - enviar_notificacao_pagamento     → SMS ao encarregado após pagamento
  - enviar_sms_mensalidade_atraso    → SMS para um encarregado específico

Tasks periódicas (agendadas pelo Celery Beat):
  - gerar_mensalidades_mes           → dia 1 de cada mês às 07:00
  - aplicar_multas_automaticas       → diário às 08:00
  - notificar_mensalidades_atraso    → diário às 09:00
  - notificar_mensalidades_a_vencer  → diário às 09:30
  - notificar_folhas_pendentes       → segundas às 08:00
"""

import logging
from datetime import date, timedelta

from celery import shared_task
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
# TASKS ASSÍNCRONAS — disparadas por eventos
# ══════════════════════════════════════════════

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='financeiro.tasks.gerar_pdf_recibo_task',
)
def gerar_pdf_recibo_task(self, recibo_id: int):
    """
    Gera o PDF de um recibo de pagamento de forma assíncrona.
    Chamada após Mensalidade.registrar_pagamento() quando estado=PAGO.
    """
    try:
        from financeiro.models import Recibo
        from financeiro.pdf_utils import gerar_pdf_recibo

        recibo = Recibo.objects.select_related(
            'mensalidade__aluno__user',
            'mensalidade__aluno__encarregado__user',
        ).get(pk=recibo_id)
        mensalidade = recibo.mensalidade

        if recibo.arquivo_pdf and recibo.arquivo_pdf.name.endswith('.pdf'):
            logger.info('Recibo %s já tem PDF — ignorado.', recibo.codigo_recibo)
            return recibo.arquivo_pdf.name

        pdf_bytes = gerar_pdf_recibo(mensalidade, recibo)
        nome = (
            f"recibo_{mensalidade.aluno.id}"
            f"_{mensalidade.mes_referente.strftime('%Y%m')}.pdf"
        )
        recibo.arquivo_pdf.save(nome, ContentFile(pdf_bytes), save=True)

        logger.info(
            'PDF gerado: recibo=%s aluno=%s',
            recibo.codigo_recibo, mensalidade.aluno.user.nome
        )
        return recibo.arquivo_pdf.name

    except Exception as exc:
        logger.error('Erro ao gerar PDF do recibo %s: %s', recibo_id, exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name='financeiro.tasks.enviar_notificacao_pagamento',
)
def enviar_notificacao_pagamento(self, mensalidade_id: int):
    """
    Envia SMS ao encarregado após pagamento confirmado de mensalidade.
    Regista resultado no LogNotificacoes.
    """
    try:
        from core.sms import enviar_sms
        from financeiro.models import LogNotificacoes, Mensalidade

        mensalidade = Mensalidade.objects.select_related(
            'aluno__user',
            'aluno__encarregado__user',
        ).get(pk=mensalidade_id)

        encarregado = mensalidade.aluno.encarregado
        if not encarregado:
            logger.warning(
                'Mensalidade %s sem encarregado — SMS ignorado.', mensalidade_id
            )
            return

        telefone = encarregado.telefone
        if not telefone:
            logger.warning(
                'Encarregado %s sem telefone — SMS ignorado.', encarregado.user.nome
            )
            return

        mensagem = (
            f"Pagamento confirmado!\n"
            f"Aluno: {mensalidade.aluno.user.nome}\n"
            f"Mes: {mensalidade.mes_referente.strftime('%m/%Y')}\n"
            f"Valor: {mensalidade.valor_pago_acumulado} MT\n"
            f"Recibo: {mensalidade.nr_fatura}"
        )

        resultado = enviar_sms(destinatario=str(telefone), mensagem=mensagem)

        LogNotificacoes.objects.create(
            mensalidade=mensalidade,
            tipo='SMS',
            destino=str(telefone),
            sucesso=resultado['sucesso'],
            resposta_server=(
                f"operador={resultado.get('operador')} "
                f"id={resultado.get('messageId','-')} "
                f"custo={resultado.get('cost','-')} "
                f"erro={resultado.get('erro','-')}"
            ),
        )

        if resultado['sucesso']:
            logger.info(
                'SMS pagamento enviado: aluno=%s operador=%s',
                mensalidade.aluno.user.nome, resultado.get('operador')
            )
        else:
            logger.error(
                'Falha ao enviar SMS: %s', resultado.get('erro')
            )
            raise self.retry(exc=Exception(resultado.get('erro')))

    except Exception as exc:
        logger.error('Erro na task enviar_notificacao_pagamento %s: %s', mensalidade_id, exc)
        raise self.retry(exc=exc)


# ══════════════════════════════════════════════
# TASKS PERIÓDICAS — agendadas pelo Celery Beat
# ══════════════════════════════════════════════

@shared_task(name='financeiro.tasks.gerar_mensalidades_mes')
def gerar_mensalidades_mes():
    """
    Gera mensalidades para todos os alunos activos sem registo
    para o mês actual. Agendada: dia 1 de cada mês às 07:00.
    """
    from financeiro.models import Mensalidade

    hoje = date.today()
    total = Mensalidade.objects.gerar_mensalidades_mes(hoje.month, hoje.year)

    logger.info(
        'gerar_mensalidades_mes: %d gerada(s) para %02d/%d.',
        total, hoje.month, hoje.year
    )
    return {'geradas': total, 'mes': hoje.month, 'ano': hoje.year}


@shared_task(name='financeiro.tasks.aplicar_multas_automaticas')
def aplicar_multas_automaticas():
    """
    Aplica multa de atraso em todas as mensalidades vencidas sem multa.
    Agendada: diário às 08:00.
    """
    from financeiro.models import Mensalidade

    pendentes = Mensalidade.objects.filter(
        estado__in=['PENDENTE', 'ATRASADO'],
        multa_atraso=0,
    )

    aplicadas = 0
    for m in pendentes:
        if m.verificar_e_aplicar_multa():
            aplicadas += 1

    logger.info('aplicar_multas_automaticas: %d multa(s) aplicada(s).', aplicadas)
    return {'aplicadas': aplicadas}


@shared_task(name='financeiro.tasks.notificar_mensalidades_atraso')
def notificar_mensalidades_atraso():
    """
    Envia SMS aos encarregados de alunos com mensalidades em atraso.
    Agendada: diário às 09:00.
    """
    from core.sms import enviar_sms_bulk
    from financeiro.models import LogNotificacoes, Mensalidade

    atrasadas = Mensalidade.objects.filter(
        estado='ATRASADO'
    ).select_related('aluno__user', 'aluno__encarregado__user')

    notificadas = 0
    for m in atrasadas:
        encarregado = m.aluno.encarregado
        if not encarregado or not encarregado.telefone:
            continue

        mensagem = (
            f"AVISO: A mensalidade de {m.aluno.user.nome} "
            f"ref. {m.mes_referente.strftime('%m/%Y')} esta em atraso. "
            f"Divida: {m.saldo_devedor} MT. "
            f"Contacte a escola."
        )

        resultado = enviar_sms(
            destinatario=str(encarregado.telefone),
            mensagem=mensagem,
        )

        LogNotificacoes.objects.create(
            mensalidade=m,
            tipo='SMS',
            destino=str(encarregado.telefone),
            sucesso=resultado['sucesso'],
            resposta_server=(
                f"operador={resultado.get('operador')} "
                f"id={resultado.get('messageId','-')} "
                f"erro={resultado.get('erro','-')}"
            ),
        )
        notificadas += 1

    logger.info(
        'notificar_mensalidades_atraso: %d SMS enviado(s).', notificadas
    )
    return {'notificadas': notificadas}


@shared_task(name='financeiro.tasks.notificar_mensalidades_a_vencer')
def notificar_mensalidades_a_vencer():
    """
    Envia SMS para mensalidades que vencem nos próximos 5 dias.
    Agendada: diário às 09:30.
    """
    from core.sms import enviar_sms
    from financeiro.models import ConfiguracaoFinanceira, LogNotificacoes, Mensalidade

    config = ConfiguracaoFinanceira.get_solo()
    hoje = date.today()
    em_5_dias = hoje + timedelta(days=5)

    pendentes = Mensalidade.objects.filter(
        estado='PENDENTE'
    ).select_related('aluno__user', 'aluno__encarregado__user')

    notificadas = 0
    for m in pendentes:
        data_limite = config.data_limite_para_mes(m.mes_referente)
        if not (hoje <= data_limite <= em_5_dias):
            continue

        encarregado = m.aluno.encarregado
        if not encarregado or not encarregado.telefone:
            continue

        mensagem = (
            f"LEMBRETE: Mensalidade de {m.aluno.user.nome} "
            f"ref. {m.mes_referente.strftime('%m/%Y')} "
            f"vence em {data_limite.strftime('%d/%m/%Y')}. "
            f"Valor: {m.saldo_devedor} MT."
        )

        resultado = enviar_sms(
            destinatario=str(encarregado.telefone),
            mensagem=mensagem,
        )

        LogNotificacoes.objects.create(
            mensalidade=m,
            tipo='SMS',
            destino=str(encarregado.telefone),
            sucesso=resultado['sucesso'],
            resposta_server=(
                f"operador={resultado.get('operador')} "
                f"id={resultado.get('messageId','-')} "
                f"erro={resultado.get('erro','-')}"
            ),
        )
        notificadas += 1

    logger.info(
        'notificar_mensalidades_a_vencer: %d SMS enviado(s).', notificadas
    )
    return {'notificadas': notificadas}


@shared_task(name='financeiro.tasks.notificar_folhas_pendentes')
def notificar_folhas_pendentes():
    """
    Regista aviso sobre folhas salariais por pagar.
    Agendada: segundas-feiras às 08:00.
    """
    from financeiro.models import FolhaPagamento

    pendentes = FolhaPagamento.objects.filter(
        status='PENDENTE'
    ).select_related('funcionario__user')

    total = pendentes.count()
    valor = sum(f.valor_total for f in pendentes)

    logger.info(
        'notificar_folhas_pendentes: %d folha(s) — %s MT.', total, valor
    )
    return {'pendentes': total, 'valor_total': str(valor)}


@shared_task(name='financeiro.tasks.invalidar_cache_dashboard')
def invalidar_cache_dashboard():
    """
    Invalida o cache do dashboard financeiro
    Chamada após pagamentos, geração de balanço e outras alterações.
    """
    from django.core.cache import cache

    cache.delete('financeiro:dashboard')
    logger.info('Cache do dashboard invalidado.')
    return {'invalidado': True}


@shared_task(
    bind=True,
    max_retries=3,
    name='financeiro.tasks.enviar_sms_manual_task'
)
def enviar_sms_manual_task(self, destinatario, mensagem):
    from core.sms import enviar_sms
    try:
        resultado = enviar_sms(destinatario, mensagem)
        if not resultado['sucesso']:
            # Se a Africa's Talking der timeout, o worker tenta de novo depois
            raise Exception(resultado.get('erro'))
        return resultado
    except Exception as exc:
        logger.error(f"Erro no envio de SMS: {exc}")
        raise self.retry(exc=exc, countdown=60)
