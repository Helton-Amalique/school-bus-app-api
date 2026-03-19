"""
financeiro/management/commands/gerar_folhas_mes.py
===================================================
Gera folhas de pagamento para todos os funcionários activos
que ainda não têm folha para o mês indicado.

Análogo ao gerar_mensalidades_mes para alunos.
Deve correr no primeiro dia de cada mês (cron: 0 6 1 * *).

Uso:
  python manage.py gerar_folhas_mes
  python manage.py gerar_folhas_mes --mes 4 --ano 2025
  python manage.py gerar_folhas_mes --dry-run
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Gera folhas de pagamento mensais para todos os funcionários activos.'

    def add_arguments(self, parser):
        parser.add_argument('--mes', type=int, default=None,
                            help='Mês a gerar (default: mês actual).')
        parser.add_argument('--ano', type=int, default=None,
                            help='Ano a gerar (default: ano actual).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Mostra o que seria gerado sem criar nada.')

    def handle(self, *args, **options):
        from financeiro.models import FolhaPagamento, Funcionario

        dry_run = options['dry_run']
        hoje = date.today()
        mes = options['mes'] or hoje.month
        ano = options['ano'] or hoje.year

        if not (1 <= mes <= 12):
            self.stdout.write(self.style.ERROR('Mês inválido. Use 1-12.'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Nenhuma folha será criada.\n'))

        data_ref = date(ano, mes, 1)

        # Funcionários activos sem folha para este mês
        funcionarios = (
            Funcionario.objects
            .filter(ativo=True)
            .exclude(
                pagamentos__mes_referente__month=mes,
                pagamentos__mes_referente__year=ano,
            )
            .select_related('user')
        )

        total = funcionarios.count()

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Todos os funcionários já têm folha para {mes:02d}/{ano}.'
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f'\n● {total} funcionário(s) sem folha para {mes:02d}/{ano}.'
            )
        )

        if dry_run:
            for f in funcionarios:
                self.stdout.write(
                    f'  [DRY-RUN] Geraria: {f.user.nome}'
                    f' — base {f.salario_base} MT'
                    f' + subsídio {f.subsidio_transporte} MT'
                    f' = {f.salario_total} MT'
                )
            self.stdout.write(
                self.style.SUCCESS(f'\n{total} folha(s) seriam geradas.')
            )
            return

        criadas = 0
        erros = 0

        with transaction.atomic():
            for funcionario in funcionarios:
                try:
                    FolhaPagamento.objects.create(
                        funcionario=funcionario,
                        mes_referente=data_ref,
                        valor_total=funcionario.salario_total,
                        status='PENDENTE',
                    )
                    self.stdout.write(
                        f'  ✓ {funcionario.user.nome}'
                        f' — {funcionario.salario_total} MT'
                    )
                    criadas += 1
                except Exception as exc:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ {funcionario.user.nome}: {exc}'
                        )
                    )
                    erros += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ {criadas} folha(s) gerada(s) para {mes:02d}/{ano}.'
            )
        )
        if erros:
            self.stdout.write(
                self.style.ERROR(f'✗ {erros} erro(s) — verificar log.')
            )
