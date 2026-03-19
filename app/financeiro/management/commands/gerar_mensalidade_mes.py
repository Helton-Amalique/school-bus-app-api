"""
Gera mensalidades para todos os alunos activos que ainda não têm
registo para o mês indicado. Deve correr no primeiro dia de cada mês.
"""

from datetime import date
from core.models import Aluno
from financeiro.models import Mensalidade
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Gera mensalidades mensais para todos os alunos activos.'

    def add_arguments(self, parser):
        parser.add_argument('--mes', type=int, default=None,
                            help='Mês a gerar (default: mês actual).')
        parser.add_argument('--ano', type=int, default=None,
                            help='Ano a gerar (default: ano actual).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Mostra quantas seriam geradas sem criar nada.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hoje = date.today()
        mes = options['mes'] or hoje.month
        ano = options['ano'] or hoje.year

        if not (1 <= mes <= 12):
            self.stdout.write(self.style.ERROR('Mês inválido. Use 1-12.'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Nenhuma mensalidade será criada.\n'))

        # Conta quantos alunos activos ainda não têm mensalidade para este mês
        alunos_sem_mensalidade = Aluno.objects.filter(ativo=True).exclude(
            historico_mensalidades__mes_referente__month=mes,
            historico_mensalidades__mes_referente__year=ano,
        )
        total_a_gerar = alunos_sem_mensalidade.count()

        if total_a_gerar == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Todos os alunos já têm mensalidade para {mes:02d}/{ano}.'
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f'\n● {total_a_gerar} aluno(s) sem mensalidade para {mes:02d}/{ano}.'
            )
        )

        if dry_run:
            for aluno in alunos_sem_mensalidade:
                self.stdout.write(
                    f'  [DRY-RUN] Geraria: {aluno.user.nome} — {aluno.mensalidade} MT'
                )
            self.stdout.write(
                self.style.SUCCESS(f'\n{total_a_gerar} mensalidade(s) seriam geradas.')
            )
            return

        total_criadas = Mensalidade.objects.gerar_mensalidades_mes(mes, ano)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ {total_criadas} mensalidade(s) gerada(s) para {mes:02d}/{ano}.'
            )
        )
