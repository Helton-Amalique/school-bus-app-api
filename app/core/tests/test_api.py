"""
tests/core/test_api.py
======================
Testes da API REST do módulo core.

Executar:
    python manage.py test tests.core.test_api
    python manage.py test tests.core.test_api.JWTTests
"""

from decimal import Decimal

from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from tests.base import BaseAPITestCase
from tests.factories import (
    criar_aluno,
    criar_encarregado,
    criar_motorista,
    criar_user,
    data_futura,
    data_nascimento_adulto,
    data_nascimento_aluno,
)


# ══════════════════════════════════════════════
# JWT
# ══════════════════════════════════════════════

class JWTTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.user = criar_user(email='jwt@teste.co.mz', role='GESTOR')

    def test_obter_token_com_credenciais_validas(self):
        resp = self.client.post('/api/v1/auth/token/', {
            'email': 'jwt@teste.co.mz',
            'password': 'Senha@1234',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_token_contem_campos_customizados(self):
        resp = self.client.post('/api/v1/auth/token/', {
            'email': 'jwt@teste.co.mz',
            'password': 'Senha@1234',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('nome', resp.data)
        self.assertIn('role', resp.data)

    def test_credenciais_erradas_retornam_401(self):
        resp = self.client.post('/api/v1/auth/token/', {
            'email': 'jwt@teste.co.mz',
            'password': 'senha_errada',
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_funciona(self):
        resp = self.client.post('/api/v1/auth/token/', {
            'email': 'jwt@teste.co.mz',
            'password': 'Senha@1234',
        })
        resp2 = self.client.post('/api/v1/auth/token/refresh/', {
            'refresh': resp.data['refresh'],
        })
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp2.data)

    def test_rota_protegida_sem_token_retorna_401(self):
        resp = self.client.get('/api/v1/users/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class UserViewSetTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.autenticar_como_gestor(email='gestor_u@teste.co.mz')

    def test_listar_utilizadores(self):
        resp = self.client.get('/api/v1/users/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_me_retorna_utilizador_autenticado(self):
        resp = self.client.get('/api/v1/users/me/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['email'], 'gestor_u@teste.co.mz')

    def test_me_sem_autenticacao_retorna_401(self):
        self.desautenticar()
        resp = self.client.get('/api/v1/users/me/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detalhe_utilizador(self):
        u = criar_user(email='detalhe@teste.co.mz')
        resp = self.client.get(f'/api/v1/users/{u.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_listagem_tem_chaves_de_paginacao(self):
        resp = self.client.get('/api/v1/users/')
        self.assertIn('count', resp.data)
        self.assertIn('results', resp.data)


class AlunoViewSetTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.autenticar_como_gestor(email='gestor_a@teste.co.mz')
        self.enc = criar_encarregado()
        self.aluno = criar_aluno(encarregado=self.enc)

    def test_listar_alunos(self):
        resp = self.client.get('/api/v1/alunos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data['count'], 1)

    def test_detalhe_aluno(self):
        resp = self.client.get(f'/api/v1/alunos/{self.aluno.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_filtrar_por_escola(self):
        resp = self.client.get('/api/v1/alunos/', {'escola_dest': 'Escola Primária Central'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data['count'], 1)


class MotoristaViewSetTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.autenticar_como_gestor(email='gestor_m@teste.co.mz')
        self.motorista = criar_motorista()

    def test_listar_motoristas(self):
        resp = self.client.get('/api/v1/motoristas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_detalhe_motorista(self):
        resp = self.client.get(f'/api/v1/motoristas/{self.motorista.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_criar_motorista_via_api(self):
        user = criar_user(role='MOTORISTA', email='novo.motor@teste.co.mz')
        payload = {
            'user': user.pk,
            'data_nascimento': data_nascimento_adulto().isoformat(),
            'nrBI': '999999999999A',
            'carta_conducao': '111111111',
            'validade_da_carta': data_futura(365).isoformat(),
            'salario': '18000.00',
        }
        resp = self.client.post('/api/v1/motoristas/', payload)
        self.assertIn(resp.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])


class EncarregadoViewSetTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.autenticar_como_gestor(email='gestor_e@teste.co.mz')
        self.enc = criar_encarregado()

    def test_listar_encarregados(self):
        resp = self.client.get('/api/v1/encarregados/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_detalhe_encarregado(self):
        resp = self.client.get(f'/api/v1/encarregados/{self.enc.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
