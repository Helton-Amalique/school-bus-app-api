"""
financeiro/management/commands/notificar_folhas_pendentes.py
============================================================
Alerta os gestores sobre folhas salariais pendentes de pagamento,
tipicamente a correr no fim de cada mês.
"""
from datetime import date
from core.models import Gestor
from django.db.models import Sum
from financeiro.models import FolhaPagamento
from django.core.management.base import BaseCommand
from django.core.mail import BadHeaderError, send_mail


REMETENTE = 'admin@schoolbus.com'


class Command(BaseCommand):
    help = 'Notifica gestores sobre folhas salariais pendentes.'

    def add_arguments(self, parser):
        parser.add_argument('--mes', type=int, default=None,
                            help='Mês a verificar (default: mês actual).')
        parser.add_argument('--ano', type=int, default=None,
                            help='Ano a verificar (default: ano actual).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Lista sem enviar e-mails.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hoje = date.today()
        mes = options['mes'] or hoje.month
        ano = options['ano'] or hoje.year

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Nenhum e-mail será enviado.\n'))

        pendentes = (
            FolhaPagamento.objects
            .filter(
                status='PENDENTE',
                mes_referente__month=mes,
                mes_referente__year=ano,
            )
            .select_related('funcionario__user')
            .order_by('funcionario__user__nome')
        )

        if not pendentes.exists():
            self.stdout.write(
                self.style.SUCCESS(f'Nenhuma folha pendente para {mes:02d}/{ano}.')
            )
            return

        total_valor = pendentes.aggregate(t=Sum('valor_total'))['t'] or 0
        self.stdout.write(
            self.style.WARNING(
                f'\n● {pendentes.count()} folha(s) pendente(s) para {mes:02d}/{ano} '
                f'| Total: {total_valor:.2f} MT'
            )
        )

        linhas = [
            f'Folhas Salariais Pendentes — {mes:02d}/{ano}\n' + '=' * 40,
            f'\n{pendentes.count()} folha(s) por pagar | Total: {total_valor:.2f} MT\n',
        ]
        for folha in pendentes:
            linha = (
                f'  • {folha.funcionario.user.nome} '
                f'({folha.funcionario.user.get_role_display()}) '
                f'— {folha.valor_total} MT'
            )
            linhas.append(linha)
            self.stdout.write(f'  {folha.funcionario.user.nome} — {folha.valor_total} MT')

        linhas.append(f'\nData: {hoje.strftime("%d/%m/%Y")}')
        corpo = '\n'.join(linhas)

        destinatarios = self._get_destinatarios()
        if not destinatarios:
            self.stdout.write(self.style.WARNING('Nenhum gestor com e-mail encontrado.'))
            return

        enviados = 0
        for email in destinatarios:
            if dry_run:
                self.stdout.write(f'\n[DRY-RUN] Enviaria para {email}')
                enviados += 1
                continue
            try:
                send_mail(
                    subject=f'[Financeiro] Folhas Salariais Pendentes — {mes:02d}/{ano}',
                    message=corpo,
                    from_email=REMETENTE,
                    recipient_list=[email],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f'✓ Enviado para {email}'))
                enviados += 1
            except BadHeaderError:
                self.stdout.write(self.style.ERROR(f'✗ Header inválido para {email}'))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'✗ Erro: {exc}'))

        self.stdout.write(
            self.style.SUCCESS(f'\nProcessamento concluído — {enviados} e-mail(s) enviado(s).')
        )

    def _get_destinatarios(self):
        return list(
            Gestor.objects.filter(ativo=True, user__email__isnull=False)
            .exclude(user__email='')
            .values_list('user__email', flat=True)
        )
