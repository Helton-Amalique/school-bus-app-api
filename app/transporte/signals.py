"""
transporte/signals.py
=====================
Signals do módulo transporte.

Signals:
  - Veiculo.post_save         → alertar documentação a vencer
  - Veiculo.pre_delete        → bloquear eliminação com rotas activas
  - Rota.pre_save             → desactivar transportes do dia se rota desactivada
  - Manutencao.post_save      → desactivar rotas ao iniciar; criar DespesaVeiculo ao concluir
  - Abastecimento.post_save   → log + criar DespesaVeiculo (COMBUSTIVEL) no financeiro
  - TransporteAluno.post_save → log de embarque/desembarque

REGRA DE DEPENDÊNCIAS:
  transporte/signals.py pode importar de `core` mas NUNCA no topo de `financeiro`.
  Imports de financeiro são feitos LOCALMENTE dentro de cada função (lazy imports)
  para evitar ciclos de importação no arranque do Django.
"""

import datetime
import logging
from django.dispatch import receiver
from financeiro.models import DespesaVeiculo
from django.core.exceptions import PermissionDenied
from django.db.models.signals import post_save, pre_delete, pre_save
from transporte.models import Abastecimento, Manutencao, Rota, TransporteAluno, Veiculo

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Veiculo)
def alertar_documentacao_veiculo(sender, instance, **kwargs):
    """
    Após guardar um Veículo, regista avisos no log para documentação
    vencida ou a vencer nos próximos 30 dias (seguro, inspecção, manifesto).
    """
    hoje   = datetime.date.today()
    limite = hoje + datetime.timedelta(days=30)

    DOCS = {
        'seguro':    instance.data_validade_seguro,
        'inspecção': instance.data_validade_inspecao,
        'manifesto': instance.data_validade_manifesto,
    }

    for nome_doc, validade in DOCS.items():
        if not validade:
            continue
        if validade < hoje:
            logger.warning(
                'Veículo %s — %s VENCIDO(A) em %s.',
                instance.matricula, nome_doc, validade
            )
        elif validade <= limite:
            logger.warning(
                'Veículo %s — %s a vencer em %s.',
                instance.matricula, nome_doc, validade
            )


@receiver(pre_delete, sender=Veiculo)
def bloquear_delete_veiculo_com_rotas(sender, instance, **kwargs):
    """
    Impede a eliminação física de um Veículo que tenha rotas associadas.
    Deve-se desactivar (ativo=False) em vez de eliminar.
    """
    if instance.rotas.exists():
        raise PermissionDenied(
            f'O veículo {instance.matricula} tem rotas associadas. '
            'Desactive o veículo em vez de o eliminar.'
        )


@receiver(pre_save, sender=Rota)
def cancelar_transportes_ao_desactivar_rota(sender, instance, **kwargs):
    """
    Quando uma Rota é desactivada (ativo: True → False),
    cancela os registos de TransporteAluno PENDENTE de hoje para esta rota.
    Registos EMBARCADO ou DESEMBARCADO são preservados.
    """
    if not instance.pk:
        return

    try:
        anterior = Rota.objects.get(pk=instance.pk)
    except Rota.DoesNotExist:
        return

    if anterior.ativo and not instance.ativo:
        cancelados = TransporteAluno.objects.filter(
            rota=instance,
            data=datetime.date.today(),
            status='PENDENTE',
        ).update(status='CANCELADO')  # cancela os transportes pendentes do dia

        logger.info(
            'Rota "%s" desactivada — %d registo(s) de transporte de hoje afectado(s).',
            instance.nome, cancelados
        )


@receiver(post_save, sender=Manutencao)
def desactivar_rotas_ao_iniciar_manutencao(sender, instance, created, **kwargs):
    """
    Quando uma Manutenção é criada (não concluída), desactiva automaticamente
    todas as rotas activas do veículo e regista um aviso.

    Quando a manutenção é concluída, regista o log mas NÃO reactiva as rotas
    automaticamente (decisão do gestor).
    """
    if created and not instance.concluida:
        rotas_afectadas = Rota.objects.filter(
            veiculo=instance.veiculo, ativo=True
        )
        count = rotas_afectadas.count()
        if count:
            rotas_afectadas.update(ativo=False)
            logger.warning(
                'Manutenção iniciada no veículo %s — %d rota(s) desactivada(s): %s.',
                instance.veiculo.matricula,
                count,
                list(rotas_afectadas.values_list('nome', flat=True)),
            )

    if not created and instance.concluida and instance.custo > 0:

        data_fim  = instance.data_fim or datetime.date.today()
        ja_existe = DespesaVeiculo.objects.filter(
            veiculo=instance.veiculo,
            tipo='MANUTENCAO',
            data=data_fim,
            valor=instance.custo,
        ).exists()

        if not ja_existe:
            try:
                DespesaVeiculo.objects.create(
                    veiculo=instance.veiculo,
                    tipo='MANUTENCAO',
                    valor=instance.custo,
                    data=data_fim,
                    km_atual=instance.quilometragem_no_momento_revisao,
                )
                logger.info(
                    'DespesaVeiculo MANUTENCAO criada: veículo=%s, custo=%s MT.',
                    instance.veiculo.matricula, instance.custo,
                )
            except Exception as exc:
                logger.error(
                    'Erro ao criar DespesaVeiculo para manutenção %s (veículo=%s): %s',
                    instance.pk, instance.veiculo.matricula, exc,
                )

    if not created and instance.concluida:
        logger.info(
            'Manutenção concluída no veículo %s (km=%s). '
            'As rotas devem ser reactivadas manualmente.',
            instance.veiculo.matricula,
            instance.quilometragem_no_momento_revisao,
        )


@receiver(post_save, sender=Abastecimento)
def lancar_abastecimento_no_financeiro(sender, instance, created, **kwargs):
    """
    Ao criar um Abastecimento, cria automaticamente uma DespesaVeiculo
    do tipo COMBUSTIVEL no módulo financeiro.

    Isto garante que o custo do combustível é reflectido no BalancoMensal
    sem necessidade de lançamento manual.

    Import local obrigatório — evita ciclo transporte → financeiro no arranque.
    """
    if not created:
        return

    try:
        DespesaVeiculo.objects.create(
            veiculo=instance.veiculo,
            tipo='COMBUSTIVEL',
            valor=instance.custo_total,
            data=instance.data,
            km_atual=instance.quilometragem_no_ato,
        )
        logger.info(
            'DespesaVeiculo COMBUSTIVEL criada: veículo=%s, %sL, %s MT, posto=%s.',
            instance.veiculo.matricula,
            instance.quantidade_litros,
            instance.custo_total,
            instance.posto_combustivel,
        )
    except Exception as exc:
        logger.error(
            'Erro ao criar DespesaVeiculo para abastecimento %s (veículo=%s): %s',
            instance.pk, instance.veiculo.matricula, exc,
        )


@receiver(post_save, sender=TransporteAluno)
def log_embarque_desembarque(sender, instance, created, **kwargs):
    """
    Regista no log cada mudança de status relevante:
    PENDENTE → EMBARCADO ou EMBARCADO → DESEMBARCADO.
    """
    if instance.status == 'EMBARCADO':
        logger.info(
            '[%s] Embarque: aluno=%s, rota=%s, veículo=%s.',
            instance.data,
            instance.aluno.user.nome,
            instance.rota.nome,
            instance.rota.veiculo.matricula,
        )
    elif instance.status == 'DESEMBARCADO':
        logger.info(
            '[%s] Desembarque: aluno=%s, rota=%s.',
            instance.data,
            instance.aluno.user.nome,
            instance.rota.nome,
        )
