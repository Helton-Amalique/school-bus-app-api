from django.test import TestCase

from rest_framework.test import APIClient
from rest_framework import status

from django.contrib.auth import get_user_model

from django.urls import reverse
from accounts.models import User

user = get_user_model()

CREATE_USER_URL = reverse("accounts:create_user")
TOKEN_URL = reverse("accounts:token")
ME_URL = reverse("accounts:me")


def create_user(**params):
    """Cria e retorna um usuário"""
    payload = {
        'email': 'test@exemplo.com',
        'password': 'testpass123',
        'nome': 'Utilizador de Test',
        'role': 'ALUNO'
    }
    payload.update(params)
    return get_user_model().objects.create_user(**payload)

class PublicUserApiTests(TestCase):
    """Testes para a API de criação de usuários"""
    def setUp(self):
        self.client = APIClient()

    def test_para_cria_usuario_sucesso(self):
        """Teste para criar um usuário com dados válidos"""
        payload = {
            "email": "test@example.com",
            "password": "testpassword123",
            "nome": "Test User",
            "role": "MOTORISTA"
        }
        response = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertEqual(user.role, payload["role"])
        self.assertNotIn("password", response.data)
        # self.assertEqual(user.nome, payload["password"])

    def test_para_criar_usuario_com_email_existente(self):
        """Erro ao criar um usuário com um email que já existe"""
        payload = {
            "email": "test@example.com",
            "password": "testpassword123",
            "nome": "Test User",
        }
        create_user(**payload)
        response = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

def test_para_criar_usuario_com_senha_curta(self):
    """Erro de a senha for inferior a o limite (ex: 8 carateres)"""
    payload = {
        "email": "test@examplo.com",
        "password": "pw",
        "nome": "Test User",
    }
    resp = self.client.post(CREATE_USER_URL, payload)
    self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
    user_exist = user().objects.filter(email=payload["email"]).exists()
    self.assertFalse(user_exist)

def create_token_for_user(self):
    """Teste para obter token com credencias validas"""
    user_details = {
        "nome": "Test User",
        "email": "test@exemplo.com",
        "password": "testpassword123",
    }
    create_user(**user_details)

    payload = {
        "email": user_details["email"],
        "password": user_details["password"],
    }
    res = self.client.post(TOKEN_URL, payload)
    self.assertEqual(res.status_code, status.HTTP_200_OK)
    self.assertIn("access", res.data)

def create_token_bad_credentials(self):
    """Erro ao tentar obter token com senha errada"""
    create_user(email="test@exemplo.com", password="goodpass")
    payload = {"email": 'test@exemplo.com', "password": "badpass"}
    res = self.client.post(TOKEN_URL, payload)
    self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
    self.assertNotIn('token', res.data)


def test_create_token_password_vazio(self):
    """password vazio retorna erro"""
    payload = {'email': 'test@exemplo.com', 'password': ''}
    res = self.client.post(TOKEN_URL, payload)

    self.assertNotIn('token', res.data)
    self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

def test_usuario_nao_autorizado(self):
    """test de autenticacao e necessario para usuarios"""
    res = self.client.get(ME_URL)
    self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateApiTests(TestCase):
    """Test que existem utilizador nao autenticado"""
    def setUp(self):
        self.user = create_user(
            email='exst@exemplo.com',
            password='testpass123',
            nome='Test nome',
            role='MOTORISTA'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retorna_perfil_sucesso(self):
        res=self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'nome': self.user.nome,
            'email': self.user.email,
            'role': self.user.role,
        })

    def test_post_me_nao_permitido(self):
        "Test post nao e permitido para o endpoint /me"
        res = self.client.post(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_perfil_usuario(self):
        """test para atualizar campos do perfil (PATCH)"""
        payload = {'nome': 'Nome Atualizado',
                   'password': 'newpass123',
                   'role': 'ENCARREGADO'}

        res = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.nome, payload['nome'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(self.user.role, payload['role'])
        self.assertEqual(res.status_code, status.HTTP_200_OK)

# class RolePermissionsTests(APITestCase):

#     def setUp(self):

#         self.admin = User.objects.create_user(
#             email="admin@test.com", nome="Admin", role="ADMIN", password="senha1234"
#         )
#         self.motorista_user = User.objects.create_user(
#             email="motorista@test.com", nome="Motorista", role="MOTORISTA", password="senha1234"
#         )
#         self.encarregado_user = User.objects.create_user(
#             email="encarregado@test.com", nome="Encarregado", role="ENCARREGADO", password="senha1234"
#         )
#         self.aluno_user = User.objects.create_user(
#             email="aluno@test.com", nome="Aluno", role="ALUNO", password="senha1234"
#         )

#         self.motorista = Motorista.objects.create(
#             user=self.motorista_user,
#             data_nascimento=date.today() - timedelta(days=365*30),
#             nrBI="123456789012Z",
#             carta_conducao="987654321",
#             validade_da_carta=date.today() + timedelta(days=365),
#             telefone="+258821234501",
#             endereco="Rua Motorista"
#         )
#         self.encarregado = Encarregado.objects.create(
#             user=self.encarregado_user,
#             nrBI="987654321098Z",
#             telefone="+258821234502",
#             endereco="Rua Encarregado"
#         )
#         self.aluno = Aluno.objects.create(
#             user=self.aluno_user,
#             data_nascimento=date.today() - timedelta(days = 365 * 10),
#             encarregado=self.encarregado,
#             nrBI="111222333444Z",
#             escola_dest="Escola Primária",
#             classe="5ª",
#             mensalidade=1500
#         )

#     def test_admin_pode_listar_alunos(self):
#         self.client.login(email="admin@test.com", password="senha1234")
#         url = reverse("core:aluno-list")
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertGreaterEqual(len(response.data), 1)

#     def test_motorista_pode_ver_se(self):
#         self.client.login(email="motorista@test.com", password="senha1234")
#         url = reverse("core:motorista-list")
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 1)
#         self.assertEqual(response.data[0]["user"]["email"], "motorista@test.com")

#     def test_somente_encarregado_pode_ver(self):
#         self.client.login(email="encarregado@test.com", password="senha1234")
#         url = reverse("core:aluno-list")
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 1)
#         self.assertEqual(response.data[0]["user"]["email"], "aluno@test.com")

#     def test_somente_aluno_pode_ver(self):
#         self.client.login(email="aluno@test.com", password="senha1234")
#         url = reverse("core:aluno-list")
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 1)
#         self.assertEqual(response.data[0]["user"]["email"], "aluno@test.com")
