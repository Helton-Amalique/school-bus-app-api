"""
transporte/management/commands/notificar_documentos_veiculo.py
==============================================================
Notifica os gestores sobre veículos com documentação vencida
ou a vencer nos próximos N dias (seguro, inspecção, manifesto).
"""

from datetime import timedelta
from core.models import Gestor
from django.utils import timezone
from transporte.models import Veiculo
from django.core.management.base import BaseCommand
from django.core.mail import BadHeaderError, send_mail


REMETENTE = 'admin@schoolbus.com'
DOCS_LABEL = {
    'data_validade_seguro': 'Seguro',
    'data_validade_inspecao': 'Inspecção',
    'data_validade_manifesto': 'Manifesto',
}


class Command(BaseCommand):
    help = 'Notifica gestores sobre documentação de veículos vencida ou a vencer.'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=30,
                            help='Janela de aviso em dias (default: 30).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Lista os veículos afectados sem enviar e-mails.')

    def handle(self, *args, **options):
        hoje = timezone.now().date()
        limite = hoje + timedelta(days=options['dias'])
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Nenhum e-mail será enviado.\n'))

        destinatarios = self._get_destinatarios()
        if not destinatarios:
            self.stdout.write(self.style.WARNING('Nenhum gestor com e-mail encontrado.'))
            return

        veiculos_activos = Veiculo.objects.filter(ativo=True).select_related(
            'motorista__user'
        )

        problemas_vencidos = []
        problemas_a_vencer = []

        for veiculo in veiculos_activos:
            for campo, label in DOCS_LABEL.items():
                validade = getattr(veiculo, campo)
                if not validade:
                    continue
                if validade < hoje:
                    problemas_vencidos.append((veiculo, label, validade))
                elif validade <= limite:
                    problemas_a_vencer.append((veiculo, label, validade))

        if not problemas_vencidos and not problemas_a_vencer:
            self.stdout.write(self.style.SUCCESS('Toda a documentação está em dia.'))
            return

        linhas = ['Relatório de Documentação de Veículos\n' + '=' * 40]

        if problemas_vencidos:
            linhas.append(f'\n🔴 DOCUMENTAÇÃO VENCIDA ({len(problemas_vencidos)} item(s)):\n')
            for v, doc, val in problemas_vencidos:
                linhas.append(
                    f'  • Veículo {v.matricula} ({v.marca} {v.modelo}) '
                    f'— {doc} venceu em {val.strftime("%d/%m/%Y")}'
                )
                self.stdout.write(
                    self.style.ERROR(
                        f'  VENCIDO  | {v.matricula} | {doc} | {val.strftime("%d/%m/%Y")}'
                    )
                )

        if problemas_a_vencer:
            linhas.append(f'\n🟡 A VENCER NOS PRÓXIMOS {options["dias"]} DIAS ({len(problemas_a_vencer)} item(s)):\n')
            for v, doc, val in problemas_a_vencer:
                linhas.append(
                    f'  • Veículo {v.matricula} ({v.marca} {v.modelo}) '
                    f'— {doc} vence em {val.strftime("%d/%m/%Y")}'
                )
                self.stdout.write(
                    self.style.WARNING(
                        f'  A VENCER | {v.matricula} | {doc} | {val.strftime("%d/%m/%Y")}'
                    )
                )

        linhas.append(f'\nData do relatório: {hoje.strftime("%d/%m/%Y")}')
        corpo = '\n'.join(linhas)

        enviados = 0
        for email in destinatarios:
            if dry_run:
                self.stdout.write(f'\n[DRY-RUN] Enviaria relatório para {email}')
                enviados += 1
                continue
            try:
                send_mail(
                    subject='[Transporte] Documentação de Veículos — Acção Necessária',
                    message=corpo,
                    from_email=REMETENTE,
                    recipient_list=[email],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f'\n✓ Relatório enviado para {email}'))
                enviados += 1
            except BadHeaderError:
                self.stdout.write(self.style.ERROR(f'✗ Header inválido para {email}'))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'✗ Erro ao enviar para {email}: {exc}'))

        self.stdout.write(
            self.style.SUCCESS(f'\nProcessamento concluído — {enviados} e-mail(s) enviado(s).')
        )

    def _get_destinatarios(self):
        """Devolve lista de e-mails de todos os gestores activos."""
        return list(
            Gestor.objects.filter(ativo=True, user__email__isnull=False)
            .exclude(user__email='')
            .values_list('user__email', flat=True)
        )
