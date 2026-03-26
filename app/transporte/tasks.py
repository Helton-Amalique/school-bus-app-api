"""
transporte/tasks.py
===================
Tasks Celery do módulo transporte.

Tasks periódicas (agendadas pelo Celery Beat):
  - notificar_cartas_conducao    → segundas às 08:30
  - notificar_documentos_veiculo → terças às 08:00
  - notificar_revisao_veiculo    → terças às 08:30
"""

import logging
from celery import shared_task
from datetime import date, timedelta

logger = logging.getLogger(__name__)


@shared_task(name='transporte.tasks.notificar_cartas_conducao')
def notificar_cartas_conducao():
    """
    Verifica motoristas com carta de condução vencida ou a vencer
    nos próximos 30 dias e regista avisos no log.

    Agendada: segundas-feiras às 08:30.
    Equivalente ao management command: notificar_cartas_conducao
    """
    from core.models import Motorista

    hoje = date.today()
    limite = hoje + timedelta(days=30)

    motoristas = Motorista.objects.filter(
        ativo=True
    ).select_related('user')

    vencidas = []
    a_vencer = []

    for m in motoristas:
        if not m.validade_da_carta:
            continue
        if m.validade_da_carta < hoje:
            vencidas.append(m.user.nome)
            logger.warning(
                'Carta VENCIDA: motorista=%s validade=%s',
                m.user.nome, m.validade_da_carta
            )
        elif m.validade_da_carta <= limite:
            a_vencer.append(m.user.nome)
            logger.warning(
                'Carta a vencer: motorista=%s validade=%s',
                m.user.nome, m.validade_da_carta
            )

    logger.info(
        'notificar_cartas_conducao: %d vencida(s), %d a vencer.',
        len(vencidas), len(a_vencer)
    )
    return {'vencidas': vencidas, 'a_vencer': a_vencer}


@shared_task(name='transporte.tasks.notificar_documentos_veiculo')
def notificar_documentos_veiculo():
    """
    Verifica veículos com documentos (seguro, inspecção) vencidos
    ou a vencer nos próximos 30 dias.

    Agendada: terças-feiras às 08:00.
    Equivalente ao management command: notificar_documentos_veiculo
    """
    from transporte.models import Veiculo

    hoje = date.today()
    limite = hoje + timedelta(days=30)

    veiculos = Veiculo.objects.filter(ativo=True)

    alertas = []
    for v in veiculos:
        problemas = []

        if v.data_seguro and v.data_seguro < hoje:
            problemas.append(f'seguro vencido em {v.data_seguro}')
        elif v.data_seguro and v.data_seguro <= limite:
            problemas.append(f'seguro vence em {v.data_seguro}')

        if v.data_inspecao and v.data_inspecao < hoje:
            problemas.append(f'inspecção vencida em {v.data_inspecao}')
        elif v.data_inspecao and v.data_inspecao <= limite:
            problemas.append(f'inspecção vence em {v.data_inspecao}')

        if problemas:
            msg = f'{v.matricula}: {", ".join(problemas)}'
            alertas.append(msg)
            logger.warning('Documentos veículo — %s', msg)

    logger.info(
        'notificar_documentos_veiculo: %d veículo(s) com alertas.', len(alertas)
    )
    return {'alertas': alertas}


@shared_task(name='transporte.tasks.notificar_revisao_veiculo')
def notificar_revisao_veiculo():
    """
    Verifica veículos que atingiram ou ultrapassaram a quilometragem
    de revisão programada.

    Agendada: terças-feiras às 08:30.
    Equivalente ao management command: notificar_revisao_veiculo
    """
    from transporte.models import Veiculo

    veiculos = Veiculo.objects.filter(ativo=True)

    necessitam_revisao = []
    for v in veiculos:
        if v.necessita_revisao():
            necessitam_revisao.append({
                'matricula': v.matricula,
                'quilometragem_atual': v.quilometragem_atual,
                'km_proxima_revisao': v.km_proxima_revisao,
            })
            logger.warning(
                'Revisão necessária: veiculo=%s km_atual=%s km_revisao=%s',
                v.matricula, v.quilometragem_atual, v.km_proxima_revisao
            )

    logger.info(
        'notificar_revisao_veiculo: %d veículo(s) a necessitar revisão.',
        len(necessitam_revisao)
    )
    return {'veiculos': necessitam_revisao}
