"""
financeiro/management/commands/notificar_mensalidades_atraso.py
===============================================================
Notifica os encarregados sobre mensalidades em atraso,
com indicação do valor em dívida e instruções de pagamento.

Uso:
  python manage.py notificar_mensalidades_atraso
  python manage.py notificar_mensalidades_atraso --dry-run
"""

from django.core.mail import BadHeaderError, send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from financeiro.models import Mensalidade

REMETENTE = 'admin@schoolbus.com'


class Command(BaseCommand):
    help = 'Notifica encarregados sobre mensalidades em atraso.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Lista os afectados sem enviar e-mails.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Nenhum e-mail será enviado.\n'))

        em_atraso = (
            Mensalidade.objects
            .filter(estado='ATRASADO')
            .select_related(
                'aluno__user',
                'aluno__encarregado__user',
            )
            .order_by('aluno__user__nome', 'mes_referente')
        )

        if not em_atraso.exists():
            self.stdout.write(self.style.SUCCESS('Nenhuma mensalidade em atraso.'))
            return

        # Agrupa por encarregado para enviar um único e-mail por família
        por_encarregado = {}
        sem_encarregado = []

        for mensalidade in em_atraso:
            encarregado = mensalidade.aluno.encarregado
            if not encarregado or not encarregado.user.email:
                sem_encarregado.append(mensalidade)
                continue
            email = encarregado.user.email
            por_encarregado.setdefault(email, {'encarregado': encarregado, 'mensalidades': []})
            por_encarregado[email]['mensalidades'].append(mensalidade)

        self.stdout.write(
            self.style.WARNING(
                f'\n● {em_atraso.count()} mensalidade(s) em atraso '
                f'| {len(por_encarregado)} encarregado(s) a notificar'
            )
        )

        if sem_encarregado:
            self.stdout.write(
                self.style.WARNING(
                    f'  ⚠ {len(sem_encarregado)} mensalidade(s) sem encarregado ou sem e-mail — ignoradas.'
                )
            )

        enviados = 0
        for email, dados in por_encarregado.items():
            enc = dados['encarregado']
            lista = dados['mensalidades']

            linhas_mensalidades = []
            total_divida = 0
            for m in lista:
                total_divida += float(m.saldo_devedor)
                linhas_mensalidades.append(
                    f'  • {m.aluno.user.nome} — '
                    f'{m.mes_referente.strftime("%m/%Y")} — '
                    f'Saldo: {m.saldo_devedor} MT'
                )

            corpo = (
                f'Prezado(a) {enc.user.nome},\n\n'
                f'Informamos que tem mensalidade(s) em atraso:\n\n'
                + '\n'.join(linhas_mensalidades) +
                f'\n\nTotal em dívida: {total_divida:.2f} MT\n\n'
                f'Por favor, proceda ao pagamento o mais brevemente possível '
                f'para evitar o bloqueio do acesso ao transporte escolar.\n\n'
                f'Para esclarecimentos, contacte a secretaria.\n\n'
                f'Atenciosamente,\nEquipa de Gestão de Transporte'
            )

            self.stdout.write(
                f'  {enc.user.nome} <{email}> — {len(lista)} mensalidade(s) | {total_divida:.2f} MT'
            )

            if dry_run:
                enviados += 1
                continue

            try:
                send_mail(
                    subject='[Transporte Escolar] Mensalidade(s) em Atraso',
                    message=corpo,
                    from_email=REMETENTE,
                    recipient_list=[email],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f' ✓ E-mail enviado'))
                enviados += 1
            except BadHeaderError:
                self.stdout.write(self.style.ERROR(f' ✗ Header inválido'))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f' ✗ Erro: {exc}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'\nProcessamento concluído — {enviados}/{len(por_encarregado)} e-mail(s) enviado(s).'
            )
        )
