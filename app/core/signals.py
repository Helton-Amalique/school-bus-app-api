"""
core/signals.py
===============
Signals do módulo core.

Signals:
  - User.post_save      → criar perfil base consoante o role (se ainda não existe)
  - Motorista.post_save → validar carta de condução + alertar se prestes a vencer
  - Aluno.post_save     → registar log de activação/desactivação
  - Aluno.pre_delete    → bloquear eliminação de alunos com histórico
  - Motorista.pre_delete → bloquear eliminação de motoristas com veículos atribuídos

REGRA DE DEPENDÊNCIAS:
  core/signals.py NUNCA importa de `financeiro` nem de `transporte` no topo.
  Imports cross-module são feitos localmente dentro da função (lazy imports)
  para evitar ciclos de importação.
"""

import logging
import datetime
from django.dispatch import receiver
from transporte.models import Veiculo
from financeiro.models import Mensalidade
from transporte.models import TransporteAluno
from django.core.exceptions import PermissionDenied
from django.db.models.signals import post_save, pre_delete, pre_save
from core.models import Aluno, Encarregado, Gestor, Monitor, Motorista, User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def criar_perfil_por_role(sender, instance, created, **kwargs):
    if not created:
        return

    logger.info(
        'User criado: %s (role=%s, id=%s). perfil deve ser explicitamente.',
        instance.email, instance.role, instance.pk
    )

@receiver(pre_save, sender=User)
def desactivar_perfil_com_user(sender, instance, **kwargs):
    """
    Quando um User é desactivado (is_active: True → False),
    desactiva também o perfil de core associado.
    """
    if not instance.pk:
        return
    try:
        anterior = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        return

    if anterior.is_active and not instance.is_active:
        PERFIS = {
            User.Cargo.ENCARREGADO: 'perfil_encarregado',
            User.Cargo.ALUNO: 'perfil_aluno',
            User.Cargo.MOTORISTA: 'perfil_motorista',
            User.Cargo.MONITOR: 'perfil_monitor',
            User.Cargo.GESTOR: 'perfil_gestor',
        }
        related = PERFIS.get(instance.role)
        if related:
            try:
                perfil = getattr(instance, related)
                if perfil.ativo:
                    perfil.ativo = False
                    perfil.save(update_fields=['ativo'])
                    logger.info(
                        'Perfil %s desactivado em cascata com o utilizador %s.',
                        instance.role, instance.email
                    )
            except Exception:
                pass


@receiver(post_save, sender=Motorista)
def alertar_carta_conducao(sender, instance, **kwargs):
    """
    Após guardar um Motorista, regista um aviso no log se a carta de condução
    estiver vencida ou prestes a vencer nos próximos 30 dias.
    """
    if not instance.validade_da_carta:
        return

    hoje = datetime.date.today()
    limite = hoje + datetime.timedelta(days=30)

    if instance.validade_da_carta < hoje:
        logger.warning(
            'Carta de condução VENCIDA: motorista=%s (validade=%s).',
            instance.user.nome, instance.validade_da_carta
        )
    elif instance.validade_da_carta <= limite:
        logger.warning(
            'Carta de condução a vencer em breve: motorista=%s (validade=%s).',
            instance.user.nome, instance.validade_da_carta
        )

@receiver(pre_delete, sender=Motorista)
def bloquear_delete_motorista_com_veiculos(sender, instance, **kwargs):
    """
    Impede a eliminação de um Motorista que ainda tenha veículos atribuídos.
    O utilizador deve primeiro desatribuir os veículos.
    """
    if Veiculo.objects.filter(motorista=instance).exists():
        raise PermissionDenied(
            f'O motorista "{instance.user.nome}" tem veículos atribuídos. '
            'Desatribua os veículos antes de eliminar o motorista.'
        )


@receiver(pre_delete, sender=Aluno)
def bloquear_delete_aluno_com_historico(sender, instance, **kwargs):
    """
    Impede a eliminação de um Aluno que tenha mensalidades ou registos
    de transporte associados. Deve-se desactivar em vez de eliminar.
    """
    tem_mensalidades = Mensalidade.objects.filter(aluno=instance).exists()
    tem_transportes = TransporteAluno.objects.filter(aluno=instance).exists()

    if tem_mensalidades or tem_transportes:
        raise PermissionDenied(
            f'O aluno "{instance.user.nome}" tem histórico financeiro ou de transporte. '
            'Desactive o aluno em vez de o eliminar.'
        )
