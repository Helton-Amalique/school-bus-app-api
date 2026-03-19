"""
financeiro/management/commands/notificar_mensalidades_a_vencer.py
=================================================================
Aviso preventivo ao encarregado X dias antes do vencimento
da mensalidade do mês corrente.
"""

from datetime import date
from django.core.management.base import BaseCommand
from django.core.mail import BadHeaderError, send_mail
from financeiro.models import ConfiguracaoFinanceira, Mensalidade

REMETENTE = 'admin@schoolbus.com'


class Command(BaseCommand):
    help = 'Envia aviso preventivo de vencimento de mensalidade ao encarregado.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias', type=int, default=5,
            help='Enviar aviso quando faltam N dias para o vencimento (default: 5).'
        )
        parser.add_argument('--dry-run', action='store_true',
                            help='Lista os afectados sem enviar e-mails.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        dias_aviso = options['dias']

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Nenhum e-mail será enviado.\n'))

        hoje = date.today()
        config = ConfiguracaoFinanceira.get_solo()

        # Mensalidades do mês corrente ainda não pagas
        pendentes = (
            Mensalidade.objects
            .filter(
                mes_referente__month=hoje.month,
                mes_referente__year=hoje.year,
                estado__in=('PENDENTE', 'PAGO_PARCIAL'),
            )
            .select_related('aluno__user', 'aluno__encarregado__user')
        )

        if not pendentes.exists():
            self.stdout.write(self.style.SUCCESS('Nenhuma mensalidade pendente este mês.'))
            return

        # Calcula data limite do mês
        data_limite = config.data_limite_para_mes(hoje.replace(day=1))
        dias_para_vencer = (data_limite - hoje).days

        if dias_para_vencer > dias_aviso:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Vencimento em {dias_para_vencer} dias ({data_limite.strftime("%d/%m/%Y")}) '
                    f'— ainda fora da janela de aviso de {dias_aviso} dias.'
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f'\n● Vencimento em {dias_para_vencer} dia(s) ({data_limite.strftime("%d/%m/%Y")}) '
                f'— {pendentes.count()} mensalidade(s) pendente(s).'
            )
        )

        # Agrupa por encarregado
        por_encarregado = {}
        sem_email = 0

        for mensalidade in pendentes:
            enc = mensalidade.aluno.encarregado
            if not enc or not enc.user.email:
                sem_email += 1
                continue
            email = enc.user.email
            por_encarregado.setdefault(email, {'encarregado': enc, 'mensalidades': []})
            por_encarregado[email]['mensalidades'].append(mensalidade)

        if sem_email:
            self.stdout.write(self.style.WARNING(f'  ⚠ {sem_email} mensalidade(s) sem e-mail — ignoradas.'))

        enviados = 0
        for email, dados in por_encarregado.items():
            enc = dados['encarregado']
            lista = dados['mensalidades']

            linhas = []
            for m in lista:
                linhas.append(
                    f'  • {m.aluno.user.nome} — '
                    f'Valor: {m.saldo_devedor} MT'
                )

            corpo = (
                f'Prezado(a) {enc.user.nome},\n\n'
                f'Este é um aviso de que a(s) mensalidade(s) abaixo vence(m) '
                f'em {data_limite.strftime("%d/%m/%Y")} '
                f'({dias_para_vencer} dia(s)):\n\n'
                + '\n'.join(linhas) +
                f'\n\nEfectue o pagamento antes da data limite para evitar a aplicação de multa.\n\n'
                f'Atenciosamente,\nEquipa de Gestão de Transporte'
            )

            self.stdout.write(f'  {enc.user.nome} <{email}> — {len(lista)} mensalidade(s)')

            if dry_run:
                enviados += 1
                continue

            try:
                send_mail(
                    subject=f'[Transporte Escolar] Mensalidade vence em {dias_para_vencer} dia(s)',
                    message=corpo,
                    from_email=REMETENTE,
                    recipient_list=[email],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS('    ✓ Enviado'))
                enviados += 1
            except BadHeaderError:
                self.stdout.write(self.style.ERROR('    ✗ Header inválido'))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'    ✗ Erro: {exc}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'\nProcessamento concluído — {enviados}/{len(por_encarregado)} e-mail(s) enviado(s).'
            )
        )
