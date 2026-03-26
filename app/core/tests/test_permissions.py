"""
tests/core/test_permissions.py
===============================
Testes das permissões granulares do sistema.

Executar:
    python manage.py test tests.core.test_permissions
    python manage.py test tests.core.test_permissions.IsGestorTests
"""

from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from core.permissions import IsGestorOuMotoristaOuMonitor
from unittest.mock import MagicMock
from tests.base import BaseAPITestCase

from tests.factories import (
    criar_aluno,
    criar_config_financeira,
    criar_encarregado,
    criar_mensalidade,
    criar_monitor,
    criar_motorista,
    criar_rota,
    criar_user,
    criar_veiculo,
)


class IsGestorTests(TestCase):

    def _permissao(self, role):
        from core.permissions import IsGestor
        from unittest.mock import MagicMock
        perm = IsGestor()
        req = MagicMock()
        req.user.is_authenticated = True
        req.user.is_staff = (role == 'ADMIN')
        req.user.role = role
        return perm.has_permission(req, None)

    def test_gestor_tem_acesso(self):
        self.assertTrue(self._permissao('GESTOR'))

    def test_admin_tem_acesso(self):
        self.assertTrue(self._permissao('ADMIN'))

    def test_motorista_nao_tem_acesso(self):
        self.assertFalse(self._permissao('MOTORISTA'))

    def test_monitor_nao_tem_acesso(self):
        self.assertFalse(self._permissao('MONITOR'))

    def test_encarregado_nao_tem_acesso(self):
        self.assertFalse(self._permissao('ENCARREGADO'))

    def test_aluno_nao_tem_acesso(self):
        self.assertFalse(self._permissao('ALUNO'))


class IsGestorOuMotoristaOuMonitorTests(TestCase):

    def _permissao(self, role):

        perm = IsGestorOuMotoristaOuMonitor()
        req  = MagicMock()
        req.user.is_authenticated = True
        req.user.is_staff = (role == 'ADMIN')
        req.user.role = role
        return perm.has_permission(req, None)

    def test_gestor_tem_acesso(self): self.assertTrue(self._permissao('GESTOR'))

    def test_motorista_tem_acesso(self): self.assertTrue(self._permissao('MOTORISTA'))

    def test_monitor_tem_acesso(self): self.assertTrue(self._permissao('MONITOR'))

    def test_encarregado_sem_acesso(self): self.assertFalse(self._permissao('ENCARREGADO'))

    def test_aluno_sem_acesso(self): self.assertFalse(self._permissao('ALUNO'))


class PodeLerMensalidadeTests(TestCase):

    def _permissao(self, role):
        from core.permissions import PodeLerMensalidade
        from unittest.mock import MagicMock
        perm = PodeLerMensalidade()
        req = MagicMock()
        req.user.is_authenticated = True
        req.user.is_staff = (role == 'ADMIN')
        req.user.role = role
        return perm.has_permission(req, None)

    def test_gestor_pode_ler(self): self.assertTrue(self._permissao('GESTOR'))

    def test_encarregado_pode_ler(self): self.assertTrue(self._permissao('ENCARREGADO'))

    def test_aluno_pode_ler(self): self.assertTrue(self._permissao('ALUNO'))

    def test_motorista_nao_pode(self): self.assertFalse(self._permissao('MOTORISTA'))

    def test_monitor_nao_pode(self): self.assertFalse(self._permissao('MONITOR'))


class PodeLerMensalidadeObjetoTests(TestCase):

    def setUp(self):
        criar_config_financeira()

    def _obj_permission(self, role, user_do_obj=None):
        from core.permissions import PodeLerMensalidade
        from unittest.mock import MagicMock
        aluno = criar_aluno()
        mens = criar_mensalidade(aluno=aluno)
        perm = PodeLerMensalidade()
        req = MagicMock()
        req.user.is_authenticated = True
        req.user.is_staff = (role == 'ADMIN')
        req.user.role = role
        req.user = user_do_obj or req.user
        return perm.has_object_permission(req, None, mens)

    def test_gestor_ve_qualquer_mensalidade(self):
        from core.permissions import PodeLerMensalidade
        from unittest.mock import MagicMock
        criar_config_financeira()
        aluno = criar_aluno()
        mens = criar_mensalidade(aluno=aluno)
        perm = PodeLerMensalidade()
        req = MagicMock()
        req.user.is_authenticated = True
        req.user.is_staff = True
        req.user.role = 'GESTOR'
        self.assertTrue(perm.has_object_permission(req, None, mens))

    def test_aluno_ve_propria_mensalidade(self):
        from core.permissions import PodeLerMensalidade
        from unittest.mock import MagicMock
        criar_config_financeira()
        aluno = criar_aluno()
        mens = criar_mensalidade(aluno=aluno)
        perm = PodeLerMensalidade()
        req = MagicMock()
        req.user.is_authenticated = True
        req.user.is_staff = False
        req.user.role = 'ALUNO'
        req.user = aluno.user
        self.assertTrue(perm.has_object_permission(req, None, mens))

    def test_aluno_nao_ve_mensalidade_de_outro(self):
        from core.permissions import PodeLerMensalidade
        from unittest.mock import MagicMock
        criar_config_financeira()
        aluno1 = criar_aluno()
        aluno2 = criar_aluno()
        mens = criar_mensalidade(aluno=aluno1)
        perm = PodeLerMensalidade()
        req = MagicMock()
        req.user.is_authenticated = True
        req.user.is_staff = False
        req.user.role = 'ALUNO'
        req.user = aluno2.user
        self.assertFalse(perm.has_object_permission(req, None, mens))

    def test_encarregado_ve_mensalidade_do_seu_aluno(self):
        from core.permissions import PodeLerMensalidade
        from unittest.mock import MagicMock
        criar_config_financeira()
        enc = criar_encarregado()
        aluno = criar_aluno(encarregado=enc)
        mens = criar_mensalidade(aluno=aluno)
        perm = PodeLerMensalidade()
        req = MagicMock()
        req.user.is_authenticated = True
        req.user.is_staff = False
        req.user.role = 'ENCARREGADO'
        req.user = enc.user
        self.assertTrue(perm.has_object_permission(req, None, mens))


# ══════════════════════════════════════════════
# TESTES DE INTEGRAÇÃO — API
# ══════════════════════════════════════════════

class UserEndpointPermissaoTests(BaseAPITestCase):
    """Testa que só GESTOR acede à lista de utilizadores."""

    def test_gestor_acede_lista_users(self):
        self.autenticar_como_gestor()
        resp = self.client.get('/api/v1/users/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_motorista_nao_acede_lista_users(self):
        self.autenticar_como_motorista()
        resp = self.client.get('/api/v1/users/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_encarregado_nao_acede_lista_users(self):
        self.autenticar_como_encarregado()
        resp = self.client.get('/api/v1/users/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonimo_nao_acede_lista_users(self):
        resp = self.client.get('/api/v1/users/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_qualquer_autenticado_acede_me(self):
        self.autenticar_como_motorista()
        resp = self.client.get('/api/v1/users/me/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class VeiculoEndpointPermissaoTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.veiculo = criar_veiculo()

    def test_gestor_lista_veiculos(self):
        self.autenticar_como_gestor()
        resp = self.client.get('/api/v1/veiculos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_motorista_lista_veiculos(self):
        self.autenticar_como_motorista()
        resp = self.client.get('/api/v1/veiculos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_encarregado_nao_lista_veiculos(self):
        self.autenticar_como_encarregado()
        resp = self.client.get('/api/v1/veiculos/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_motorista_nao_cria_veiculo(self):
        self.autenticar_como_motorista()
        resp = self.client.post('/api/v1/veiculos/', {})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_gestor_pode_criar_veiculo(self):
        self.autenticar_como_gestor()
        from tests.factories import criar_motorista, data_futura
        m = criar_motorista()
        resp = self.client.post('/api/v1/veiculos/', {
            'marca': 'Toyota', 'modelo': 'Hiace',
            'matricula': 'PER-001-XY', 'capacidade': 15,
            'motorista': m.pk,
            'data_validade_seguro': data_futura(365).isoformat(),
            'data_validade_inspecao': data_futura(365).isoformat(),
            'data_validade_manifesto': data_futura(365).isoformat(),
            'nr_manifesto': 'MAN12345',
        })
        self.assertIn(resp.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])


class RotaEndpointPermissaoTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.rota = criar_rota()

    def test_gestor_lista_rotas(self):
        self.autenticar_como_gestor()
        resp = self.client.get('/api/v1/rotas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_motorista_lista_rotas(self):
        self.autenticar_como_motorista()
        resp = self.client.get('/api/v1/rotas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_monitor_lista_rotas(self):
        self._autenticar(criar_monitor().user)
        resp = self.client.get('/api/v1/rotas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_encarregado_nao_cria_rota(self):
        self.autenticar_como_encarregado()
        resp = self.client.post('/api/v1/rotas/', {})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class MensalidadeEndpointPermissaoTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.aluno = criar_aluno(mensalidade=Decimal('2500.00'))
        self.mensalidade = criar_mensalidade(aluno=self.aluno)

    def test_gestor_lista_mensalidades(self):
        self.autenticar_como_gestor()
        resp = self.client.get('/api/v1/mensalidades/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_encarregado_lista_mensalidades(self):
        enc = self.aluno.encarregado
        self._autenticar(enc.user)
        resp = self.client.get('/api/v1/mensalidades/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_aluno_lista_mensalidades(self):
        self._autenticar(self.aluno.user)
        resp = self.client.get('/api/v1/mensalidades/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_motorista_nao_lista_mensalidades(self):
        self.autenticar_como_motorista()
        resp = self.client.get('/api/v1/mensalidades/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_monitor_nao_lista_mensalidades(self):
        self._autenticar(criar_monitor().user)
        resp = self.client.get('/api/v1/mensalidades/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_encarregado_nao_pode_pagar_mensalidade(self):
        enc = self.aluno.encarregado
        self._autenticar(enc.user)
        resp = self.client.post(
            f'/api/v1/mensalidades/{self.mensalidade.pk}/pagar/',
            {'valor': '2500.00', 'metodo': 'DINHEIRO'},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_gestor_pode_pagar_mensalidade(self):
        self.autenticar_como_gestor()
        resp = self.client.post(
            f'/api/v1/mensalidades/{self.mensalidade.pk}/pagar/',
            {'valor': str(self.mensalidade.valor_base), 'metodo': 'TRANSFERENCIA'},
        )
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])


class BalancoEndpointPermissaoTests(BaseAPITestCase):

    def test_gestor_acede_dashboard(self):
        self.autenticar_como_gestor()
        resp = self.client.get('/api/v1/balancos/dashboard/')
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_motorista_nao_acede_dashboard(self):
        self.autenticar_como_motorista()
        resp = self.client.get('/api/v1/balancos/dashboard/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_encarregado_nao_acede_balanco(self):
        self.autenticar_como_encarregado()
        resp = self.client.get('/api/v1/balancos/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonimo_nao_gera_balanco(self):
        resp = self.client.post('/api/v1/balancos/gerar/', {'mes': 3, 'ano': 2025})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
