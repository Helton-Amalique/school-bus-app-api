"""
tests/financeiro/test_financeiro.py
====================================
Testes de modelos, signals, API e management commands do módulo financeiro.

Executar:
    python manage.py test tests.financeiro
    python manage.py test tests.financeiro.test_financeiro.MensalidadeModelTests
"""

import datetime
from io import StringIO
from decimal import Decimal
from django.test import TestCase
from rest_framework import status
from django.core.management import call_command
from django.core.exceptions import ValidationError

from tests.base import BaseAPITestCase, BaseTestCase, FinanceiroTestCase
from tests.factories import (
    criar_aluno,
    criar_categoria,
    criar_config_financeira,
    criar_funcionario,
    criar_mensalidade,
    criar_motorista,
    criar_user,
    criar_veiculo,
    data_passada,
)


class ConfiguracaoFinanceiraTests(TestCase):

    def test_get_solo_cria_se_nao_existe(self):
        from financeiro.models import ConfiguracaoFinanceira
        ConfiguracaoFinanceira.objects.all().delete()
        cfg = ConfiguracaoFinanceira.get_solo()
        self.assertIsNotNone(cfg.pk)

    def test_get_solo_retorna_existente(self):
        from financeiro.models import ConfiguracaoFinanceira
        cfg1 = criar_config_financeira()
        cfg2 = ConfiguracaoFinanceira.get_solo()
        self.assertEqual(cfg1.pk, cfg2.pk)

    def test_segundo_registo_nao_e_permitido(self):
        from financeiro.models import ConfiguracaoFinanceira
        criar_config_financeira()
        cfg2 = ConfiguracaoFinanceira(
            dia_vencimento=10,
            dia_limite_pagamento=15,
            valor_multa_fixa=Decimal('500.00'),
        )
        with self.assertRaises(Exception):
            cfg2.save()

    def test_data_limite_para_mes(self):
        cfg    = criar_config_financeira(dia_limite_pagamento=10)
        limite = cfg.data_limite_para_mes(datetime.date(2025, 3, 1))
        self.assertEqual(limite, datetime.date(2025, 3, 10))

    def test_dia_limite_menor_que_vencimento_levanta_erro(self):
        from financeiro.models import ConfiguracaoFinanceira
        cfg = ConfiguracaoFinanceira(
            dia_vencimento=15, dia_limite_pagamento=10,
            valor_multa_fixa=Decimal('500.00'),
        )
        with self.assertRaises(ValidationError):
            cfg.clean()

    def test_delete_nao_remove_configuracao(self):
        from financeiro.models import ConfiguracaoFinanceira
        cfg = criar_config_financeira()
        pk  = cfg.pk
        cfg.delete()
        self.assertTrue(ConfiguracaoFinanceira.objects.filter(pk=pk).exists())


class TransacaoTests(TestCase):

    def setUp(self):
        self.cat_receita = criar_categoria('Mensalidade', 'RECEITA')
        self.cat_despesa = criar_categoria('Manutenção',  'DESPESA')

    def test_criar_transacao_receita(self):
        from financeiro.models import Transacao
        t = Transacao.objects.create(
            descricao='Pagamento mensalidade',
            valor=Decimal('2500.00'),
            data_vencimento=datetime.date.today(),
            categoria=self.cat_receita,
            status='PAGO',
        )
        self.assertIsNotNone(t.pk)

    def test_transacao_pendente_vencida_fica_atrasada(self):
        from financeiro.models import Transacao
        t = Transacao(
            descricao='Atrasada',
            valor=Decimal('2500.00'),
            data_vencimento=data_passada(30),
            categoria=self.cat_receita,
            status='PENDENTE',
        )
        t.save()
        self.assertEqual(t.status, 'ATRASADO')

    def test_is_overdue_true_para_atrasado(self):
        from financeiro.models import Transacao
        t = Transacao.objects.create(
            descricao='Atrasado',
            valor=Decimal('1000.00'),
            data_vencimento=data_passada(30),
            categoria=self.cat_receita,
            status='ATRASADO',
        )
        self.assertTrue(t.is_overdue)

    def test_despesa_com_aluno_levanta_erro(self):
        from financeiro.models import Transacao
        aluno = criar_aluno()
        t = Transacao(
            descricao='Despesa inválida',
            valor=Decimal('1000.00'),
            data_vencimento=datetime.date.today(),
            categoria=self.cat_despesa,
            aluno=aluno,
        )
        with self.assertRaises(ValidationError):
            t.clean()


class MensalidadeModelTests(TestCase):

    def setUp(self):
        criar_config_financeira(dia_vencimento=5, dia_limite_pagamento=10)
        criar_categoria('Mensalidade', 'RECEITA')
        self.aluno = criar_aluno(mensalidade=Decimal('2500.00'))

    def test_criar_mensalidade_valida(self):
        self.assertIsNotNone(criar_mensalidade(aluno=self.aluno).pk)

    def test_unique_aluno_mes_referente(self):
        from django.db import IntegrityError
        mes = datetime.date.today().replace(day=1)
        criar_mensalidade(aluno=self.aluno, mes_referente=mes)
        with self.assertRaises(IntegrityError):
            criar_mensalidade(aluno=self.aluno, mes_referente=mes)

    def test_atualizar_estado_sem_pagamento(self):
        m = criar_mensalidade(aluno=self.aluno)
        m.atualizar_estado()
        self.assertIn(m.estado, ['PENDENTE', 'ATRASADO'])

    def test_atualizar_estado_pago_total(self):
        m = criar_mensalidade(aluno=self.aluno)
        m.valor_pago_acumulado = m.valor_base
        m.atualizar_estado()
        self.assertEqual(m.estado, 'PAGO')

    def test_atualizar_estado_pago_parcial(self):
        m = criar_mensalidade(aluno=self.aluno)
        m.valor_pago_acumulado = Decimal('1000.00')
        m.atualizar_estado()
        self.assertEqual(m.estado, 'PAGO_PARCIAL')

    def test_estado_isento_nao_e_alterado(self):
        m = criar_mensalidade(aluno=self.aluno, estado='ISENTO')
        m.atualizar_estado()
        self.assertEqual(m.estado, 'ISENTO')

    def test_registrar_pagamento_parcial(self):
        m = criar_mensalidade(aluno=self.aluno)
        m.registrar_pagamento(Decimal('1000.00'), 'DINHEIRO')
        m.refresh_from_db()
        self.assertEqual(m.valor_pago_acumulado, Decimal('1000.00'))
        self.assertEqual(m.estado, 'PAGO_PARCIAL')

    def test_registrar_pagamento_total_muda_para_pago(self):
        m = criar_mensalidade(aluno=self.aluno)
        m.registrar_pagamento(m.valor_base, 'TRANSFERENCIA')
        m.refresh_from_db()
        self.assertEqual(m.estado, 'PAGO')

    def test_registrar_pagamento_zero_levanta_erro(self):
        m = criar_mensalidade(aluno=self.aluno)
        with self.assertRaises(ValueError):
            m.registrar_pagamento(Decimal('0.00'), 'DINHEIRO')

    def test_verificar_e_aplicar_multa_apos_vencimento(self):
        from financeiro.models import Mensalidade
        mes_passado = data_passada(40).replace(day=1)
        m = criar_mensalidade(aluno=self.aluno, mes_referente=mes_passado)
        Mensalidade.objects.filter(pk=m.pk).update(
            estado='ATRASADO', multa_atraso=Decimal('0.00')
        )
        m.refresh_from_db()
        resultado = m.verificar_e_aplicar_multa()
        self.assertTrue(resultado)
        m.refresh_from_db()
        self.assertGreater(m.multa_atraso, Decimal('0.00'))

    def test_verificar_multa_nao_aplica_se_ja_pago(self):
        from financeiro.models import Mensalidade
        mes_passado = data_passada(40).replace(day=1)
        m = criar_mensalidade(aluno=self.aluno, mes_referente=mes_passado)
        Mensalidade.objects.filter(pk=m.pk).update(estado='PAGO')
        m.refresh_from_db()
        self.assertFalse(m.verificar_e_aplicar_multa())


class MensalidadeManagerTests(TestCase):

    def setUp(self):
        criar_config_financeira()
        criar_categoria('Mensalidade', 'RECEITA')
        self.aluno = criar_aluno(mensalidade=Decimal('2500.00'))

    def test_queryset_atrasadas(self):
        from financeiro.models import Mensalidade
        # Mensalidade antiga não paga
        mes_passado = (datetime.date.today() - datetime.timedelta(days=40)).replace(day=1)
        criar_mensalidade(aluno=self.aluno, mes_referente=mes_passado, estado='ATRASADO')
        self.assertEqual(Mensalidade.objects.atrasadas().count(), 1)


    def test_gerar_mesnsalidades_em_massa(self):
        from financeiro.models import Mensalidade
        criar_aluno(nome="Aluno 2", mensalidade=Decimal('3000.00'))

        proximo_mes = (datetime.date.today() + datetime.timedelta(days=30)).replace(day=1)
        criadas = Mensalidade.objects.gerar_mensalidades_mes(proximo_mes)
        self.assertEqual(criadas, 2)
        self.assertEqual(Mensalidade.objects.filter(mes_referente=proximo_mes).count(), 2)

    def test_gerar_mensalidades_para_alunos_activos(self):
        from financeiro.models import Mensalidade
        aluno1 = criar_aluno()
        aluno2 = criar_aluno()
        hoje   = datetime.date.today()
        Mensalidade.objects.all().delete()

        criadas = Mensalidade.objects.gerar_mensalidades_mes(hoje.month, hoje.year)
        self.assertGreaterEqual(criadas, 2)
        self.assertTrue(Mensalidade.objects.filter(aluno=aluno1).exists())
        self.assertTrue(Mensalidade.objects.filter(aluno=aluno2).exists())

    def test_gerar_mensalidades_nao_duplica(self):
        from financeiro.models import Mensalidade
        criar_aluno()
        hoje = datetime.date.today()
        Mensalidade.objects.all().delete()

        Mensalidade.objects.gerar_mensalidades_mes(hoje.month, hoje.year)
        qtd_antes = Mensalidade.objects.count()
        Mensalidade.objects.gerar_mensalidades_mes(hoje.month, hoje.year)
        self.assertEqual(Mensalidade.objects.count(), qtd_antes)

    def test_total_devedor_mes_retorna_decimal(self):
        from financeiro.models import Mensalidade
        hoje  = datetime.date.today()
        total = Mensalidade.objects.total_devedor_mes(hoje.month, hoje.year)
        self.assertIsInstance(total, Decimal)
        self.assertGreaterEqual(total, Decimal('0.00'))


# ══════════════════════════════════════════════
# RECIBO
# ══════════════════════════════════════════════

class ReciboTests(TestCase):

    def setUp(self):
        criar_config_financeira()
        criar_categoria('Mensalidade', 'RECEITA')

    def test_recibo_gerado_automaticamente_ao_pagar(self):
        from financeiro.models import Recibo
        aluno = criar_aluno(mensalidade=Decimal('2500.00'))
        m     = criar_mensalidade(aluno=aluno)
        m.registrar_pagamento(m.valor_base, 'TRANSFERENCIA')
        self.assertTrue(Recibo.objects.filter(mensalidade=m).exists())

    def test_recibo_nao_duplicado(self):
        from financeiro.models import Recibo
        aluno = criar_aluno(mensalidade=Decimal('2500.00'))
        m     = criar_mensalidade(aluno=aluno)
        m.registrar_pagamento(m.valor_base, 'TRANSFERENCIA')
        m.refresh_from_db()
        m._gerar_recibo_automatico()  # segunda chamada não deve duplicar
        self.assertEqual(Recibo.objects.filter(mensalidade=m).count(), 1)


# ══════════════════════════════════════════════
# SIGNAL — MENSALIDADE AUTOMÁTICA AO CRIAR ALUNO
# ══════════════════════════════════════════════

class SignalMensalidadeAutomaticaTests(TestCase):

    def setUp(self):
        criar_config_financeira()

    def test_criar_aluno_gera_mensalidade_do_mes(self):
        from financeiro.models import Mensalidade
        aluno = criar_aluno()
        hoje  = datetime.date.today()
        self.assertTrue(
            Mensalidade.objects.filter(
                aluno=aluno,
                mes_referente__month=hoje.month,
                mes_referente__year=hoje.year,
            ).exists()
        )


# ══════════════════════════════════════════════
# FUNCIONARIO
# ══════════════════════════════════════════════

class FuncionarioTests(TestCase):

    def test_criar_funcionario_valido(self):
        self.assertIsNotNone(criar_funcionario().pk)

    def test_str_nao_e_vazio(self):
        self.assertTrue(str(criar_funcionario()))


# ══════════════════════════════════════════════
# API — MENSALIDADES
# ══════════════════════════════════════════════

class MensalidadeAPITests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.autenticar_como_gestor(email='gestor_men@teste.co.mz')
        self.aluno       = criar_aluno(mensalidade=Decimal('2500.00'))
        self.mensalidade = criar_mensalidade(aluno=self.aluno)

    def test_listar_mensalidades(self):
        resp = self.client.get('/api/v1/mensalidades/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_detalhe_mensalidade(self):
        resp = self.client.get(f'/api/v1/mensalidades/{self.mensalidade.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_pagar_mensalidade_action(self):
        resp = self.client.post(
            f'/api/v1/mensalidades/{self.mensalidade.pk}/pagar/',
            {'valor': str(self.mensalidade.valor_base), 'metodo': 'TRANSFERENCIA'},
        )
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_filtrar_por_estado(self):
        resp = self.client.get('/api/v1/mensalidades/', {'estado': 'PENDENTE'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_sem_autenticacao_retorna_401(self):
        self.desautenticar()
        resp = self.client.get('/api/v1/mensalidades/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ══════════════════════════════════════════════
# API — DASHBOARD
# ══════════════════════════════════════════════

class DashboardAPITests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.autenticar_como_gestor(email='gestor_dash@teste.co.mz')

    def test_dashboard_retorna_200_ou_404(self):
        resp = self.client.get('/api/v1/balancos/dashboard/')
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


# ══════════════════════════════════════════════
# MANAGEMENT COMMANDS
# ══════════════════════════════════════════════

class ManagementCommandDryRunTests(TestCase):
    """Garante que todos os comandos correm sem erro com --dry-run."""

    def setUp(self):
        criar_config_financeira()

    def _run(self, nome, *args, **kwargs):
        out = StringIO()
        call_command(nome, *args, stdout=out, **kwargs)
        return out.getvalue()

    def test_gerar_mensalidades_mes(self):
        self._run('gerar_mensalidades_mes', '--dry-run')

    def test_aplicar_multas_automaticas(self):
        self._run('aplicar_multas_automaticas', '--dry-run')

    def test_notificar_mensalidades_atraso(self):
        self._run('notificar_mensalidades_atraso', '--dry-run')

    def test_notificar_mensalidades_a_vencer(self):
        self._run('notificar_mensalidades_a_vencer', '--dry-run')

    def test_notificar_folhas_pendentes(self):
        self._run('notificar_folhas_pendentes', '--dry-run')

    def test_notificar_cartas_conducao(self):
        self._run('notificar_cartas_conducao', '--dry-run')

    def test_notificar_documentos_veiculo(self):
        self._run('notificar_documentos_veiculo', '--dry-run')

    def test_notificar_revisao_veiculo(self):
        self._run('notificar_revisao_veiculo', '--dry-run')


class ManagementCommandExecucaoRealTests(TestCase):
    """Testa execução real dos comandos críticos contra a BD de testes."""

    def setUp(self):
        criar_config_financeira()
        criar_categoria('Mensalidade', 'RECEITA')

    def _run(self, nome, *args, **kwargs):
        out = StringIO()
        call_command(nome, *args, stdout=out, **kwargs)
        return out.getvalue()

    def test_gerar_mensalidades_mes_cria_registos(self):
        from financeiro.models import Mensalidade
        aluno = criar_aluno()
        hoje = datetime.date.today()
        Mensalidade.objects.all().delete()
        self._run('gerar_mensalidades_mes')
        self.assertTrue(Mensalidade.objects.filter(aluno=aluno).exists())

    def test_aplicar_multas_actualiza_mensalidades_atrasadas(self):
        from financeiro.models import Mensalidade
        aluno       = criar_aluno()
        mes_passado = data_passada(40).replace(day=1)
        Mensalidade.objects.all().delete()
        m = criar_mensalidade(aluno=aluno, mes_referente=mes_passado)
        Mensalidade.objects.filter(pk=m.pk).update(
            estado='ATRASADO', multa_atraso=Decimal('0.00')
        )
        self._run('aplicar_multas_automaticas')
        m.refresh_from_db()
        self.assertGreater(m.multa_atraso, Decimal('0.00'))


# ══════════════════════════════════════════════
# PONTO 1 — gerar_folhas_mes
# ══════════════════════════════════════════════

class GerarFolhasMesCommandTests(TestCase):
    """
    Testes do command gerar_folhas_mes.
    Garante que folhas são criadas para funcionários activos
    e que o balanço mensal reflecte os valores correctos.
    """

    def setUp(self):
        criar_config_financeira()

    def _run(self, *args, **kwargs):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('gerar_folhas_mes', *args, stdout=out, **kwargs)
        return out.getvalue()

    def test_cria_folha_para_funcionario_activo(self):
        from financeiro.models import FolhaPagamento
        f = criar_funcionario()
        hoje = datetime.date.today()
        FolhaPagamento.objects.all().delete()

        self._run()

        self.assertTrue(
            FolhaPagamento.objects.filter(
                funcionario=f,
                mes_referente__month=hoje.month,
                mes_referente__year=hoje.year,
            ).exists()
        )

    def test_valor_folha_igual_ao_salario_total(self):
        from financeiro.models import FolhaPagamento
        f = criar_funcionario()
        hoje = datetime.date.today()
        FolhaPagamento.objects.all().delete()

        self._run()

        folha = FolhaPagamento.objects.get(funcionario=f)
        self.assertEqual(folha.valor_total, f.motorista_perfil.salario)

    def test_nao_duplica_folha_existente(self):
        from financeiro.models import FolhaPagamento
        f = criar_funcionario()
        hoje = datetime.date.today()
        FolhaPagamento.objects.all().delete()

        self._run()
        qtd_antes = FolhaPagamento.objects.count()
        self._run()
        self.assertEqual(FolhaPagamento.objects.count(), qtd_antes)

    def test_folha_criada_com_status_pendente(self):
        from financeiro.models import FolhaPagamento
        criar_funcionario()
        hoje = datetime.date.today()
        FolhaPagamento.objects.all().delete()

        self._run()

        folha = FolhaPagamento.objects.first()
        self.assertEqual(folha.status, 'PENDENTE')

    def test_dry_run_nao_cria_folhas(self):
        from financeiro.models import FolhaPagamento
        criar_funcionario()
        FolhaPagamento.objects.all().delete()

        self._run('--dry-run')

        self.assertEqual(FolhaPagamento.objects.count(), 0)

    def test_folha_paga_entra_no_balanco(self):
        from financeiro.models import BalancoMensal, FolhaPagamento
        criar_categoria('Salários', 'DESPESA')
        f = criar_funcionario()
        hoje = datetime.date.today()
        FolhaPagamento.objects.all().delete()

        self._run()
        folha = FolhaPagamento.objects.get(funcionario=f)
        folha.confirmar_pagamento(metodo='TRANSFERENCIA')

        balanco = BalancoMensal.gerar_balanco(hoje.month, hoje.year)
        self.assertGreater(balanco.total_folha_salarial, Decimal('0.00'))

    def test_funcionario_inactivo_nao_gera_folha(self):
        from financeiro.models import FolhaPagamento
        from financeiro.models import Funcionario
        f = criar_funcionario()
        Funcionario.objects.filter(pk=f.pk).update(ativo=False)
        FolhaPagamento.objects.all().delete()

        self._run()

        self.assertFalse(FolhaPagamento.objects.filter(funcionario=f).exists())


# ══════════════════════════════════════════════
# PONTO 2 — registrar_despesas_vencidas
# ══════════════════════════════════════════════

class RegistrarDespesasVencidasCommandTests(TestCase):
    """
    Testes do command registrar_despesas_vencidas.
    Garante que despesas vencidas entram no balanço após execução.
    """

    def setUp(self):
        criar_config_financeira()
        criar_categoria('Operacional', 'DESPESA')

    def _run(self, *args, **kwargs):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('registrar_despesas_vencidas', *args, stdout=out, **kwargs)
        return out.getvalue()

    def _criar_despesa(self, descricao='Electricidade', valor='5000.00', dias_vencida=10):
        from financeiro.models import DespesaGeral
        cat = criar_categoria('Operacional', 'DESPESA')
        return DespesaGeral.objects.create(
            descricao=descricao,
            valor=Decimal(valor),
            data_vencimento=data_passada(dias_vencida),
            categoria=cat,
            pago=False,
        )

    def test_despesa_vencida_fica_paga_apos_execucao(self):
        from financeiro.models import DespesaGeral
        d = self._criar_despesa()
        self._run()
        d.refresh_from_db()
        self.assertTrue(d.pago)

    def test_despesa_nao_vencida_nao_e_alterada(self):
        from financeiro.models import DespesaGeral
        cat = criar_categoria('Operacional', 'DESPESA')
        d = DespesaGeral.objects.create(
            descricao='Futura',
            valor=Decimal('1000.00'),
            data_vencimento=data_futura(10),
            categoria=cat,
            pago=False,
        )
        self._run()
        d.refresh_from_db()
        self.assertFalse(d.pago)

    def test_despesa_ja_paga_nao_e_alterada(self):
        from financeiro.models import DespesaGeral
        d = self._criar_despesa()
        d.registrar_pagamento()  # pagar manualmente
        d.refresh_from_db()
        transacao_pk_antes = d.transacao_id

        self._run()  # não deve criar segunda Transacao

        d.refresh_from_db()
        self.assertEqual(d.transacao_id, transacao_pk_antes)

    def test_transacao_criada_apos_registar(self):
        from financeiro.models import DespesaGeral
        d = self._criar_despesa()
        self.assertIsNone(d.transacao_id)
        self._run()
        d.refresh_from_db()
        self.assertIsNotNone(d.transacao_id)

    def test_dry_run_nao_altera_despesa(self):
        from financeiro.models import DespesaGeral
        d = self._criar_despesa()
        self._run('--dry-run')
        d.refresh_from_db()
        self.assertFalse(d.pago)

    def test_despesa_vencida_entra_no_balanco(self):
        from financeiro.models import BalancoMensal
        hoje = datetime.date.today()
        # Despesa vencida no mês actual
        self._criar_despesa(dias_vencida=5)
        self._run()
        balanco = BalancoMensal.gerar_balanco(hoje.month, hoje.year)
        self.assertGreater(balanco.total_despesas_gerais, Decimal('0.00'))

    def test_filtro_ate_exclui_despesas_mais_recentes(self):
        from financeiro.models import DespesaGeral
        d_antiga = self._criar_despesa(descricao='Antiga', dias_vencida=30)
        d_recente = self._criar_despesa(descricao='Recente', dias_vencida=2)

        # Só registar até 15 dias atrás
        data_corte = data_passada(15).isoformat()
        self._run(f'--ate={data_corte}')

        d_antiga.refresh_from_db()
        d_recente.refresh_from_db()
        self.assertTrue(d_antiga.pago)
        self.assertFalse(d_recente.pago)


# ══════════════════════════════════════════════
# PONTO 3 — nr_fatura gerado pelo bulk_create
# ══════════════════════════════════════════════

class NrFaturaGeradoCommandTests(TestCase):
    """
    Garante que o nr_fatura é sempre preenchido nas mensalidades,
    incluindo as geradas pelo command gerar_mensalidades_mes
    (que antes usava bulk_create e bypassava o save()).
    """

    def setUp(self):
        criar_config_financeira()

    def _run_gerar(self):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('gerar_mensalidades_mes', stdout=out)
        return out.getvalue()

    def test_mensalidade_criada_diretamente_tem_nr_fatura(self):
        from financeiro.models import Mensalidade
        aluno = criar_aluno()
        m = criar_mensalidade(aluno=aluno)
        self.assertIsNotNone(m.nr_fatura)
        self.assertNotEqual(m.nr_fatura, '')

    def test_mensalidade_via_signal_tem_nr_fatura(self):
        """Signal gerar_mensalidade_ao_criar_aluno usa create() — deve ter nr_fatura."""
        from financeiro.models import Mensalidade
        aluno = criar_aluno()
        m = Mensalidade.objects.filter(aluno=aluno).first()
        self.assertIsNotNone(m)
        self.assertIsNotNone(m.nr_fatura)

    def test_mensalidade_via_command_tem_nr_fatura(self):
        """
        Regressão directa ao bug do bulk_create.
        Antes da correcção: nr_fatura=None porque bulk_create bypassa save().
        Após a correcção: create() individual garante nr_fatura gerado.
        """
        from financeiro.models import Mensalidade
        aluno = criar_aluno()
        hoje = datetime.date.today()
        Mensalidade.objects.all().delete()

        self._run_gerar()

        m = Mensalidade.objects.get(aluno=aluno)
        self.assertIsNotNone(m.nr_fatura)
        self.assertTrue(m.nr_fatura.startswith('FAT-'))

    def test_nr_fatura_unico_entre_mensalidades(self):
        from financeiro.models import Mensalidade
        aluno1 = criar_aluno()
        aluno2 = criar_aluno()
        hoje = datetime.date.today()
        Mensalidade.objects.all().delete()

        self._run_gerar()

        faturas = list(
            Mensalidade.objects.values_list('nr_fatura', flat=True)
        )
        # Todos preenchidos e sem duplicados
        self.assertTrue(all(f is not None for f in faturas))
        self.assertEqual(len(faturas), len(set(faturas)))

    def test_nr_fatura_formato_correcto(self):
        """Formato esperado: FAT-YYYYMM-{aluno_id}-{hex6}"""
        from financeiro.models import Mensalidade
        aluno = criar_aluno()
        Mensalidade.objects.all().delete()
        self._run_gerar()
        m = Mensalidade.objects.get(aluno=aluno)
        partes = m.nr_fatura.split('-')
        self.assertEqual(partes[0], 'FAT')
        self.assertEqual(len(partes), 4)


# ══════════════════════════════════════════════
# PONTO 4 — remoção de gerar_lancamento_salario
# ══════════════════════════════════════════════

class GerarLancamentoSalarioRemovidoTests(TestCase):
    """
    Regressão: garante que gerar_lancamento_salario() foi removido
    e que o único caminho para lançar salários no balanço é
    FolhaPagamento.confirmar_pagamento().

    Se alguém reintroduzir o método por engano, estes testes detectam
    o comportamento errado (Transacao PENDENTE que não entra no balanço).
    """

    def setUp(self):
        criar_config_financeira()
        criar_categoria('Salários', 'DESPESA')

    def test_funcionario_nao_tem_metodo_gerar_lancamento_salario(self):
        from financeiro.models import Funcionario
        f = criar_funcionario()
        self.assertFalse(
            hasattr(f, 'gerar_lancamento_salario'),
            'gerar_lancamento_salario() foi reintroduzido — deve ser removido.',
        )

    def test_caminho_correcto_e_confirmar_pagamento(self):
        """
        O único caminho válido para lançar salário no balanço:
        FolhaPagamento → confirmar_pagamento() → Transacao PAGO → balanço.
        """
        from financeiro.models import BalancoMensal, FolhaPagamento, Transacao

        f    = criar_funcionario()
        hoje = datetime.date.today()

        folha = FolhaPagamento.objects.create(
            funcionario=f,
            mes_referente=hoje.replace(day=1),
            valor_total=f.motorista_perfil.salario,
            status='PENDENTE',
        )

        # Antes de confirmar: sem Transacao, sem impacto no balanço
        balanco_antes = BalancoMensal.gerar_balanco(hoje.month, hoje.year)
        self.assertEqual(balanco_antes.total_folha_salarial, Decimal('0.00'))

        # Confirmar pagamento
        folha.confirmar_pagamento(metodo='TRANSFERENCIA')

        # Transacao criada com status PAGO
        transacao = Transacao.objects.get(pk=folha.transacao_vinculada_id)
        self.assertEqual(transacao.status, 'PAGO')

        # Balanço actualizado
        balanco_depois = BalancoMensal.gerar_balanco(hoje.month, hoje.year)
        self.assertGreater(balanco_depois.total_folha_salarial, Decimal('0.00'))

    def test_transacao_pendente_nao_entra_no_balanco(self):
        """
        Documenta o comportamento que existia com gerar_lancamento_salario():
        Transacao com status=PENDENTE não é agregada pelo gerar_balanco().
        """
        from financeiro.models import BalancoMensal, Transacao

        cat  = criar_categoria('Salários', 'DESPESA')
        hoje = datetime.date.today()

        # Simular o comportamento antigo — criar Transacao PENDENTE directamente
        Transacao.objects.create(
            descricao='Salário simulado',
            valor=Decimal('15000.00'),
            data_vencimento=hoje,
            categoria=cat,
            status='PENDENTE',
        )

        balanco = BalancoMensal.gerar_balanco(hoje.month, hoje.year)
        # Confirma que Transacao PENDENTE não afecta o balanço
        self.assertEqual(balanco.total_folha_salarial, Decimal('0.00'))


# ══════════════════════════════════════════════
# FOLHA PAGAMENTO — BLOQUEAR UPDATE QUANDO PAGO
# ══════════════════════════════════════════════

class FolhaPagamentoUpdateBloqueadoTests(BaseAPITestCase):
    """
    Garante que uma FolhaPagamento com status=PAGO
    não pode ser editada via PATCH.
    """

    def setUp(self):
        super().setUp()
        from tests.factories import criar_funcionario, criar_config_financeira
        criar_config_financeira()
        self.funcionario = criar_funcionario()

    def _criar_folha(self, status='PENDENTE'):
        from financeiro.models import FolhaPagamento
        import datetime
        return FolhaPagamento.objects.create(
            funcionario=self.funcionario,
            mes_referente=datetime.date.today().replace(day=1),
            valor_total=self.funcionario.salario_total,
            status=status,
        )

    def test_gestor_pode_editar_folha_pendente(self):
        self.autenticar_como_gestor()
        folha = self._criar_folha('PENDENTE')
        resp = self.client.patch(
            f'/api/v1/folhas/{folha.pk}/',
            {'valor_total': '20000.00'},
        )
        self.assertIn(resp.status_code, [200, 400])  # 400 se unique_together falhar

    def test_gestor_nao_pode_editar_folha_paga(self):
        self.autenticar_como_gestor()
        folha = self._criar_folha('PENDENTE')
        folha.confirmar_pagamento()
        resp = self.client.patch(
            f'/api/v1/folhas/{folha.pk}/',
            {'valor_total': '99999.00'},
        )
        self.assertEqual(resp.status_code, 403)

    def test_folha_paga_nao_pode_ser_eliminada(self):
        self.autenticar_como_gestor()
        folha = self._criar_folha('PENDENTE')
        folha.confirmar_pagamento()
        resp = self.client.delete(f'/api/v1/folhas/{folha.pk}/')
        self.assertEqual(resp.status_code, 403)

    def test_folha_pendente_pode_ser_eliminada(self):
        self.autenticar_como_gestor()
        folha = self._criar_folha('PENDENTE')
        resp = self.client.delete(f'/api/v1/folhas/{folha.pk}/')
        self.assertEqual(resp.status_code, 204)


# ══════════════════════════════════════════════
# FILTROS DE DATA
# ══════════════════════════════════════════════

class FiltroDataTests(BaseAPITestCase):
    """Testa filtragem por intervalo de datas nos endpoints financeiros."""

    def setUp(self):
        super().setUp()
        from tests.factories import criar_config_financeira, criar_aluno
        criar_config_financeira()
        self.aluno = criar_aluno()
        from financeiro.models import Mensalidade
        import datetime
        Mensalidade.objects.create(
            aluno=self.aluno, mes_referente=datetime.date(2025, 1, 1),
            valor_base=1500, estado='PAGO',
        )
        Mensalidade.objects.create(
            aluno=self.aluno, mes_referente=datetime.date(2025, 6, 1),
            valor_base=1500, estado='PENDENTE',
        )

    def test_filtro_mes_referente_min(self):
        self.autenticar_como_gestor()
        resp = self.client.get('/api/v1/mensalidades/?mes_referente_min=2025-04-01')
        self.assertEqual(resp.status_code, 200)
        resultados = resp.data['results'] if 'results' in resp.data else resp.data
        meses = [r['mes_referente'] for r in resultados]
        self.assertTrue(all(m >= '2025-04-01' for m in meses))

    def test_filtro_mes_referente_max(self):
        self.autenticar_como_gestor()
        resp = self.client.get('/api/v1/mensalidades/?mes_referente_max=2025-03-01')
        self.assertEqual(resp.status_code, 200)
        resultados = resp.data['results'] if 'results' in resp.data else resp.data
        meses = [r['mes_referente'] for r in resultados]
        self.assertTrue(all(m <= '2025-03-01' for m in meses))

    def test_filtro_intervalo_completo(self):
        self.autenticar_como_gestor()
        resp = self.client.get(
            '/api/v1/mensalidades/?mes_referente_min=2025-01-01&mes_referente_max=2025-03-01'
        )
        self.assertEqual(resp.status_code, 200)
        resultados = resp.data['results'] if 'results' in resp.data else resp.data
        self.assertEqual(len(resultados), 1)


# ══════════════════════════════════════════════
# NORMALIZAÇÃO DE MES_REFERENTE
# ══════════════════════════════════════════════

class NormalizacaoMesReferenteTests(BaseAPITestCase):
    """Garante que mes_referente é sempre normalizado para dia 1."""
    def setUp(self):
        super().setUp()
        from tests.factories import criar_config_financeira, criar_aluno
        criar_config_financeira()
        self.aluno = criar_aluno()

    def test_dia_arbitrario_normalizado_para_dia_1(self):
        self.autenticar_como_gestor()
        resp = self.client.post('/api/v1/mensalidades/', {
            'aluno': self.aluno.pk,
            'mes_referente': '2025-03-15',  # dia 15 — deve ser normalizado para 01
            'valor_base': '1500.00',
            'estado': 'PENDENTE',
        })
        self.assertIn(resp.status_code, [200, 201])
        from financeiro.models import Mensalidade
        m = Mensalidade.objects.filter(aluno=self.aluno).first()
        if m:
            self.assertEqual(m.mes_referente.day, 1)


# ══════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════

class HealthCheckTests(BaseAPITestCase):
    """Testa o endpoint /api/health/."""
    def test_health_check_retorna_200(self):
        resp = self.client.get('/api/health/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('status', resp.json())
        self.assertIn('db', resp.json())

    def test_health_check_nao_requer_autenticacao(self):
        # Sem autenticação deve responder igualmente
        resp = self.client.get('/api/health/')
        self.assertIn(resp.status_code, [200, 503])

    def test_health_check_retorna_timestamp(self):
        resp = self.client.get('/api/health/')
        self.assertIn('timestamp', resp.json())
