"""
financeiro/signals.py
=====================
REGRA CRÍTICA: nenhum modelo é importado no topo deste ficheiro.
Todos os imports de modelos são feitos LOCALMENTE dentro de cada função.

Razão: imports de topo em signals.py causam referências circulares durante
o arranque do Django, resultando em UnboundLocalError ou AppRegistryNotReady.
"""

import logging
from datetime import date
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save

logger = logging.getLogger(__name__)


@receiver(post_save, sender='core.Aluno')
def gerar_mensalidade_ao_criar_aluno(sender, instance, created, **kwargs):
    if not created or not instance.ativo:
        return

    from financeiro.models import Mensalidade

    hoje = date.today()
    data_ref = hoje.replace(day=1)

    existe = Mensalidade.objects.filter(
        aluno=instance,
        mes_referente__month=hoje.month,
        mes_referente__year=hoje.year,
    ).exists()

    if not existe:
        try:
            Mensalidade.objects.create(
                aluno=instance,
                mes_referente=data_ref,
                valor_base=instance.mensalidade,
                estado='PENDENTE',
            )
            logger.info('Mensalidade de %s/%s gerada para o aluno %s.', hoje.month, hoje.year, instance.user.nome)
        except Exception as exc:
            logger.error('Erro ao gerar mensalidade para o aluno %s: %s', instance.user.nome, exc)


@receiver(pre_save, sender='financeiro.Mensalidade')
def actualizar_estado_mensalidade(sender, instance, **kwargs):
    if not instance.pk:
        return
    if instance.estado == 'ISENTO':
        return
    instance.atualizar_estado()


@receiver(pre_save, sender='financeiro.Mensalidade')
def log_mudanca_estado_mensalidade(sender, instance, **kwargs):
    if not instance.pk:
        return

    from financeiro.models import Mensalidade

    try:
        anterior = Mensalidade.objects.get(pk=instance.pk)
    except Mensalidade.DoesNotExist:
        return

    if anterior.estado != instance.estado:
        logger.info(
            'Mensalidade %s — estado: %s → %s (aluno=%s, mês=%s).',
            instance.nr_fatura or instance.pk,
            anterior.estado, instance.estado,
            instance.aluno.user.nome,
            instance.mes_referente.strftime('%m/%Y'),
        )


@receiver(post_save, sender='financeiro.Mensalidade')
def aplicar_multa_automatica(sender, instance, created, **kwargs):
    if created:
        return
    if instance.estado in ('PAGO', 'ISENTO'):
        return
    if instance.multa_atraso > 0:
        return

    from financeiro.models import ConfiguracaoFinanceira, Mensalidade

    config = ConfiguracaoFinanceira.get_solo()
    data_limite = config.data_limite_para_mes(instance.mes_referente)

    if date.today() > data_limite and instance.saldo_devedor > 0:
        Mensalidade.objects.filter(pk=instance.pk).update(
            multa_atraso=config.valor_multa_fixa,
            estado='ATRASADO',
        )
        logger.info('Multa de %.2f MT aplicada à mensalidade %s.', config.valor_multa_fixa, instance.nr_fatura or instance.pk)


@receiver(post_save, sender='financeiro.Mensalidade')
def emitir_recibo_ao_pagar(sender, instance, created, **kwargs):
    if created:
        return
    if instance.estado != 'PAGO':
        return

    from financeiro.models import Recibo

    if Recibo.objects.filter(mensalidade=instance).exists():
        return

    try:
        instance._gerar_recibo_automatico()
        logger.info('Recibo gerado para a mensalidade %s (aluno=%s).', instance.nr_fatura or instance.pk, instance.aluno.user.nome)
    except Exception as exc:
        logger.error('Erro ao gerar recibo para %s: %s', instance.nr_fatura or instance.pk, exc)


@receiver(post_save, sender='financeiro.FolhaPagamento')
def log_folha_pagamento(sender, instance, created, **kwargs):
    if created:
        logger.info('Folha criada: %s, mês=%s, valor=%s MT.', instance.funcionario.user.nome, instance.mes_referente.strftime('%m/%Y'), instance.valor_total)
    elif instance.status == 'PAGO':
        logger.info('Folha PAGA: %s, mês=%s, valor=%s MT.', instance.funcionario.user.nome, instance.mes_referente.strftime('%m/%Y'), instance.valor_total)


@receiver(post_save, sender='financeiro.DespesaVeiculo')
def log_despesa_veiculo(sender, instance, created, **kwargs):
    if created:
        logger.info('Despesa frota: veículo=%s, tipo=%s, valor=%s MT.', instance.veiculo.matricula, instance.get_tipo_display(), instance.valor)


@receiver(post_save, sender='financeiro.DespesaGeral')
def log_despesa_geral(sender, instance, created, **kwargs):
    if created:
        logger.info('Despesa geral criada: "%s", %s MT.', instance.descricao, instance.valor)
    elif instance.pago:
        logger.info('Despesa geral PAGA: "%s", %s MT.', instance.descricao, instance.valor)
