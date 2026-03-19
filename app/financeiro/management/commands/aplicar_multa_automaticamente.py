"""
financeiro/management/commands/aplicar_multas_automaticas.py
============================================================
Percorre todas as mensalidades em atraso sem multa aplicada
e aplica a multa configurada. Deve correr diariamente via cron.

O signal `aplicar_multa_automatica` só actua quando a mensalidade
é guardada — se não houver actividade no sistema, este comando
garante que nenhuma mensalidade fica sem multa indefinidamente.
"""

from datetime import date
from django.core.management.base import BaseCommand
from financeiro.models import ConfiguracaoFinanceira, Mensalidade

class Command(BaseCommand):
    help = 'Aplica multas a todas as mensalidades em atraso sem multa registada.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Lista as mensalidades afectadas sem aplicar multas.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Nenhuma multa será aplicada.\n'))

        config = ConfiguracaoFinanceira.get_solo()
        hoje   = date.today()

        candidatas = (
            Mensalidade.objects
            .filter(
                estado__in=('PENDENTE', 'ATRASADO', 'PAGO_PARCIAL'),
                multa_atraso=0,
            )
            .select_related('aluno__user')
        )

        a_multar = []
        for m in candidatas:
            data_limite = config.data_limite_para_mes(m.mes_referente)
            if hoje > data_limite and m.saldo_devedor > 0:
                a_multar.append(m)

        if not a_multar:
            self.stdout.write(
                self.style.SUCCESS('Nenhuma mensalidade a necessitar de multa.')
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f'\n● {len(a_multar)} mensalidade(s) a receber multa de {config.valor_multa_fixa} MT:'
            )
        )

        aplicadas = 0
        for m in a_multar:
            self.stdout.write(
                f'  {m.aluno.user.nome} — {m.mes_referente.strftime("%m/%Y")} '
                f'| Saldo: {m.saldo_devedor} MT'
            )
            if dry_run:
                aplicadas += 1
                continue

            Mensalidade.objects.filter(pk=m.pk).update(
                multa_atraso=config.valor_multa_fixa,
                estado='ATRASADO',
            )
            aplicadas += 1

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n[DRY-RUN] {aplicadas} multa(s) seriam aplicadas.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ {aplicadas} multa(s) aplicada(s) ({config.valor_multa_fixa} MT cada).'
                )
            )
