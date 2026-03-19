"""
tests/base.py
=============
Classes base reutilizáveis para todos os testes do projecto.

Substitui o conftest.py do pytest — sem qualquer dependência externa.
Usa apenas django.test.TestCase e rest_framework.test.APITestCase.

Uso:
    from tests.base import BaseTestCase, BaseAPITestCase, FinanceiroTestCase

    class MeuTeste(BaseTestCase):
        def test_algo(self):
            aluno = self.criar_aluno_padrao()
            ...

    class MinhaAPITeste(BaseAPITestCase):
        def test_lista(self):
            self.autenticar_como_gestor()
            resp = self.client.get('/api/v1/alunos/')
            self.assertEqual(resp.status_code, 200)
"""

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import (
    criar_aluno,
    criar_categoria,
    criar_config_financeira,
    criar_encarregado,
    criar_gestor,
    criar_mensalidade,
    criar_monitor,
    criar_motorista,
    criar_rota,
    criar_user,
    criar_veiculo,
)


# ══════════════════════════════════════════════
# BASE — TestCase simples
# ══════════════════════════════════════════════

class BaseTestCase(TestCase):
    """
    TestCase base para testes de modelos e signals.

    Fornece:
      - dados mínimos criados no setUp (config financeira + categorias)
      - helpers para criar entidades rapidamente
    """

    @classmethod
    def setUpTestData(cls):
        """
        Dados partilhados por todos os testes da classe.
        setUpTestData é executado uma vez por classe, em vez de uma vez por teste —
        muito mais rápido quando há muitos testes na mesma classe.
        """
        super().setUpTestData()
        cls.config = criar_config_financeira()
        cls.cat_receita = criar_categoria('Mensalidade', 'RECEITA')
        cls.cat_despesa = criar_categoria('Manutenção', 'DESPESA')
        cls.cat_abastec = criar_categoria('Abastecimento', 'DESPESA')
        cls.cat_salario = criar_categoria('Salário', 'DESPESA')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def criar_aluno_padrao(self, mensalidade=Decimal('2500.00'), **kwargs):
        return criar_aluno(mensalidade=mensalidade, **kwargs)

    def criar_motorista_padrao(self, **kwargs):
        return criar_motorista(**kwargs)

    def criar_veiculo_padrao(self, motorista=None, **kwargs):
        if motorista is None:
            motorista = self.criar_motorista_padrao()
        return criar_veiculo(motorista=motorista, **kwargs)

    def criar_rota_padrao(self, veiculo=None, **kwargs):
        if veiculo is None:
            veiculo = self.criar_veiculo_padrao()
        return criar_rota(veiculo=veiculo, **kwargs)

    def criar_mensalidade_padrao(self, aluno=None, **kwargs):
        if aluno is None:
            aluno = self.criar_aluno_padrao()
        return criar_mensalidade(aluno=aluno, **kwargs)


# ══════════════════════════════════════════════
# BASE — APITestCase
# ══════════════════════════════════════════════

class BaseAPITestCase(APITestCase):
    """
    APITestCase base para testes de ViewSets e endpoints.

    Fornece:
      - autenticar_como_gestor / motorista / encarregado
      - desautenticar
      - dados mínimos no setUp
    """

    def setUp(self):
        super().setUp()
        criar_config_financeira()
        criar_categoria('Mensalidade', 'RECEITA')
        criar_categoria('Manutenção', 'DESPESA')
        criar_categoria('Abastecimento', 'DESPESA')
        criar_categoria('Salário', 'DESPESA')

    # ------------------------------------------------------------------
    # Autenticação
    # ------------------------------------------------------------------

    def _autenticar(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
        return user

    def autenticar_como_gestor(self, email='gestor@teste.co.mz', **kwargs):
        user = criar_user(role='GESTOR', email=email, **kwargs)
        return self._autenticar(user)

    def autenticar_como_motorista(self, email='motorista@teste.co.mz'):
        m = criar_motorista()
        # Actualizar email do user criado pela factory
        m.user.email = email
        m.user.save(update_fields=['email'])
        return self._autenticar(m.user)

    def autenticar_como_encarregado(self, email='enc@teste.co.mz'):
        enc = criar_encarregado()
        enc.user.email = email
        enc.user.save(update_fields=['email'])
        return self._autenticar(enc.user)

    def desautenticar(self):
        self.client.credentials()


# ══════════════════════════════════════════════
# BASE — módulo financeiro (inclui dados extra)
# ══════════════════════════════════════════════

class FinanceiroTestCase(BaseTestCase):
    """
    Extensão do BaseTestCase com dados adicionais para o módulo financeiro.
    Útil para testes de Mensalidade, Recibo, Balanço.
    """
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.aluno = criar_aluno(mensalidade=Decimal('2500.00'))
