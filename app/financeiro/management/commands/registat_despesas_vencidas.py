"""
financeiro/management/commands/registrar_despesas_vencidas.py
=============================================================
Regista automaticamente como pagas as DespesasGerais cujo
data_vencimento já passou e cujo campo `pago` ainda é False.

Contexto:
  O balanço mensal só agrega DespesaGeral onde pago=True.
  Sem este comando, despesas que vencem mas não são manualmente
  confirmadas ficam permanentemente fora do balanço.

Modo de operação:
  - Por omissão, considera despesas vencidas até hoje.
  - Metodo de pagamento default: TRANSFERENCIA (configurável via --metodo).
  - Suporta --ate para limitar a data de corte.
  - Suporta --dry-run para auditoria sem alterações.

Deve correr diariamente (cron: 0 8 * * *).

Uso:
  python manage.py registrar_despesas_vencidas
  python manage.py registrar_despesas_vencidas --ate 2025-03-31
  python manage.py registrar_despesas_vencidas --metodo DINHEIRO
  python manage.py registrar_despesas_vencidas --dry-run
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Regista como pagas as despesas gerais vencidas ainda não confirmadas.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ate',
            type=str,
            default=None,
            help='Data de corte YYYY-MM-DD (default: hoje).',
        )
        parser.add_argument(
            '--metodo',
            type=str,
            default='TRANSFERENCIA',
            choices=['DINHEIRO', 'TRANSFERENCIA', 'CARTAO', 'OUTRO'],
            help='Método de pagamento a registar (default: TRANSFERENCIA).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Lista sem aplicar alterações.',
        )

    def handle(self, *args, **options):
        from financeiro.models import DespesaGeral

        dry_run = options['dry_run']
        metodo = options['metodo']
        hoje = date.today()

        if options['ate']:
            try:
                data_corte = date.fromisoformat(options['ate'])
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Formato de data inválido. Use YYYY-MM-DD.')
                )
                return
        else:
            data_corte = hoje

        if dry_run:
            self.stdout.write(
                self.style.WARNING('[DRY-RUN] Nenhuma despesa será alterada.\n')
            )

        pendentes = (
            DespesaGeral.objects
            .filter(pago=False, data_vencimento__lte=data_corte)
            .select_related('categoria')
            .order_by('data_vencimento')
        )

        total = pendentes.count()

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Nenhuma despesa geral vencida até {data_corte.strftime("%d/%m/%Y")}.'
                )
            )
            return

        valor_total = sum(d.valor for d in pendentes)

        self.stdout.write(
            self.style.WARNING(
                f'\n● {total} despesa(s) vencida(s) até {data_corte.strftime("%d/%m/%Y")}'
                f' | Total: {valor_total:.2f} MT'
            )
        )

        processadas = 0
        erros = 0

        for despesa in pendentes:
            linha = (
                f'  {despesa.data_vencimento.strftime("%d/%m/%Y")}'
                f' | {despesa.descricao[:50]}'
                f' | {despesa.valor} MT'
                f' | {despesa.categoria.nome}'
            )

            if dry_run:
                self.stdout.write(f'  [DRY-RUN] Registaria: {linha}')
                processadas += 1
                continue

            try:
                despesa.registrar_pagamento(metodo=metodo)
                self.stdout.write(self.style.SUCCESS(f'  ✓{linha}'))
                processadas += 1
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f' ✗ {despesa.descricao[:40]}: {exc}')
                )
                erros += 1

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n{processadas} despesa(s) seriam registadas ({valor_total:.2f} MT).'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ {processadas} despesa(s) registada(s) ({valor_total:.2f} MT).'
                )
            )
            if erros:
                self.stdout.write(
                    self.style.ERROR(f'✗ {erros} erro(s) — verificar log.')
                )
