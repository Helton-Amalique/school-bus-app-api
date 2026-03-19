"""
transporte/management/commands/notificar_revisao_veiculo.py
===========================================================
Notifica os gestores sobre veículos que atingiram a quilometragem
de revisão e não têm manutenção em curso.
"""

from core.models import Gestor
from django.utils import timezone
from transporte.models import Veiculo
from django.core.management.base import BaseCommand
from django.core.mail import BadHeaderError, send_mail

REMETENTE = 'admin@schoolbus.com'


class Command(BaseCommand):
    help = 'Notifica gestores sobre veículos que necessitam de revisão.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Lista os veículos sem enviar e-mails.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Nenhum e-mail será enviado.\n'))

        destinatarios = self._get_destinatarios()
        if not destinatarios:
            self.stdout.write(self.style.WARNING('Nenhum gestor com e-mail encontrado.'))
            return

        # Filtra veículos que precisam de revisão (método do modelo)
        veiculos_activos = Veiculo.objects.filter(ativo=True).select_related(
            'motorista__user'
        ).prefetch_related('manutencoes')

        a_rever = [v for v in veiculos_activos if v.precisa_manutencao()]

        if not a_rever:
            self.stdout.write(self.style.SUCCESS('Nenhum veículo necessita de revisão.'))
            return

        self.stdout.write(
            self.style.WARNING(f'\n● {len(a_rever)} veículo(s) a necessitar de revisão:')
        )

        linhas = [
            'Relatório de Revisões de Veículos\n' + '=' * 40,
            f'\n🔧 {len(a_rever)} VEÍCULO(S) NECESSITAM DE REVISÃO:\n',
        ]

        for v in a_rever:
            excesso = v.quilometragem_atual - v.km_proxima_revisao
            linha = (
                f'  • {v.matricula} ({v.marca} {v.modelo}) '
                f'— Km actual: {v.quilometragem_atual} '
                f'| Km revisão: {v.km_proxima_revisao} '
                f'| Excesso: +{excesso} km'
            )
            linhas.append(linha)
            self.stdout.write(self.style.WARNING(f'  {v.matricula} | {v.quilometragem_atual} km | revisão aos {v.km_proxima_revisao} km'))

        linhas.append(f'\nData do relatório: {timezone.now().date().strftime("%d/%m/%Y")}')
        corpo = '\n'.join(linhas)

        enviados = 0
        for email in destinatarios:
            if dry_run:
                self.stdout.write(f'\n[DRY-RUN] Enviaria relatório para {email}')
                enviados += 1
                continue
            try:
                send_mail(
                    subject='[Transporte] Veículos a Necessitar de Revisão',
                    message=corpo,
                    from_email=REMETENTE,
                    recipient_list=[email],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f'✓ Relatório enviado para {email}'))
                enviados += 1
            except BadHeaderError:
                self.stdout.write(self.style.ERROR(f'✗ Header inválido para {email}'))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'✗ Erro ao enviar para {email}: {exc}'))

        self.stdout.write(
            self.style.SUCCESS(f'\nProcessamento concluído — {enviados} e-mail(s) enviado(s).')
        )

    def _get_destinatarios(self):
        return list(
            Gestor.objects.filter(ativo=True, user__email__isnull=False)
            .exclude(user__email='')
            .values_list('user__email', flat=True)
        )