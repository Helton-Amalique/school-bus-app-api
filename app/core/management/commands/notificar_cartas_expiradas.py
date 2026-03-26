"""
core/management/commands/notificar_cartas_conducao.py
=====================================================
Envia e-mail aos motoristas com carta de condução vencida ou
a vencer nos próximos N dias (default: 30).
"""

from datetime import timedelta
from django.utils import timezone
from core.models import Motorista
from django.core.management.base import BaseCommand
from django.core.mail import send_mail, BadHeaderError

REMETENTE = 'admin@schoolbus.com'

class Command(BaseCommand):
    help = 'Notifica motoristas com carta de condução vencida ou a vencer em breve.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=30,
            help='Janela de aviso em dias (default: 30).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Lista os motoristas afectados sem enviar e-mails.',
        )

    def handle(self, *args, **options):
        hoje = timezone.now().date()
        limite = hoje + timedelta(days=options['dias'])
        dry_run = options['dry_run']

        expirados = Motorista.objects.filter(
            data_validade_carta__lt=hoje,
            ativo=True,
        ).select_related('user')

        a_vencer = Motorista.objects.filter(
            data_validade_carta__gte=hoje,
            data_validade_carta__lte=limite,
            ativo=True,
        ).select_related('user')

        total_expirados = expirados.count()
        total_a_vencer = a_vencer.count()

        if total_expirados == 0 and total_a_vencer == 0:
            self.stdout.write(self.style.SUCCESS('Nenhum motorista requer notificação.'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Nenhum e-mail será enviado.\n'))

        if total_expirados:
            self.stdout.write(
                self.style.ERROR(f'\n● {total_expirados} carta(s) VENCIDA(S):')
            )
            enviados = self._enviar_lote(
                motoristas=expirados,
                assunto='Carta de Condução Vencida',
                template=lambda m: (
                    f'Prezado(a) {m.user.nome},\n\n'
                    f'A sua carta de condução venceu em {m.data_validade_carta.strftime("%d/%m/%Y")}.\n'
                    f'Por favor, regularize a sua situação o mais brevemente possível.\n\n'
                    f'Atenciosamente,\nEquipa de Gestão de Transporte'
                ),
                dry_run=dry_run,
            )
            self.stdout.write(
                self.style.SUCCESS(f'→ {enviados}/{total_expirados} e-mail(s) enviado(s).')
            )

        if total_a_vencer:
            self.stdout.write(
                self.style.WARNING(f'\n● {total_a_vencer} carta(s) a vencer nos próximos {options["dias"]} dias:')
            )
            enviados = self._enviar_lote(
                motoristas=a_vencer,
                assunto='Carta de Condução Próxima de Vencer',
                template=lambda m: (
                    f'Prezado(a) {m.user.nome},\n\n'
                    f'A sua carta de condução expira em {m.data_validade_carta.strftime("%d/%m/%Y")}.\n'
                    f'Por favor, proceda à renovação com antecedência.\n\n'
                    f'Atenciosamente,\nEquipa de Gestão de Transporte'
                ),
                dry_run=dry_run,
            )
            self.stdout.write(
                self.style.SUCCESS(f' → {enviados}/{total_a_vencer} e-mail(s) enviado(s).')
            )

        self.stdout.write(self.style.SUCCESS('\nProcessamento concluído.'))

    def _enviar_lote(self, motoristas, assunto, template, dry_run):
        """Itera os motoristas, envia (ou simula) e-mail, devolve o total enviado."""
        enviados = 0
        for motorista in motoristas:
            email = motorista.user.email
            nome = motorista.user.nome

            if not email:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠ {nome} — sem e-mail registado, ignorado.')
                )
                continue

            if dry_run:
                self.stdout.write(f'  [DRY-RUN] Enviaria para {nome} <{email}>')
                enviados += 1
                continue

            try:
                send_mail(
                    subject=assunto,
                    message=template(motorista),
                    from_email=REMETENTE,
                    recipient_list=[email],
                    fail_silently=False,
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✓ E-mail enviado para {nome} <{email}>')
                )
                enviados += 1
            except BadHeaderError:
                self.stdout.write(
                    self.style.ERROR(f'✗ Header inválido para {email} — ignorado.')
                )
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f'✗ Erro ao enviar para {email}: {exc}')
                )

        return enviados
