import datetime
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from core.models import Aluno, Encarregado, Motorista, Gestor, Monitor

User = get_user_model()


def make_user(email, nome, role, password='Test1234!', **kwargs):
    return User.objects.create_user(
        email=email, nome=nome, role=role, password=password, **kwargs
    )

def make_encarregado(nome='Encarregado Teste'):
    user = make_user(f'{nome.replace(" ","").lower()}@test.com', nome, 'ENCARREGADO')
    return Encarregado.objects.create(
        user=user, nrBI='123456789012A', telefone='+258841234567'
    )

def make_aluno(encarregado=None, nome='Aluno Teste'):
    if encarregado is None:
        encarregado = make_encarregado()
    user = make_user(f'{nome.replace(" ","").lower()}@test.com', nome, 'ALUNO')
    return Aluno.objects.create(
        user=user,
        encarregado=encarregado,
        data_nascimento=datetime.date(2010, 5, 15),
        nrBI='987654321012B',
        escola_dest='Escola Primária Central',
        classe='5ª Classe',
        mensalidade='1500.00',
    )

def make_motorista(nome='Motorista Teste'):
    user = make_user(f'{nome.replace(" ","").lower()}@test.com', nome, 'MOTORISTA')
    return Motorista.objects.create(
        user=user,
        data_nascimento=datetime.date(1985, 3, 20),
        nrBI='111222333012C',
        carta_conducao='123456789',
        validade_da_carta=datetime.date.today() + datetime.timedelta(days=365),
        salario='25000.00',
    )

def make_gestor(nome='Gestor Teste', departamento='GERAL'):
    user = make_user(f'{nome.replace(" ","").lower()}@test.com', nome, 'GESTOR')
    return Gestor.objects.create(
        user=user,
        data_nascimento=datetime.date(1980, 1, 10),
        nrBI='444555666012D',
        departamento=departamento,
        salario='40000.00',
    )

def make_monitor(nome='Monitor Teste'):
    user = make_user(f'{nome.replace(" ","").lower()}@test.com', nome, 'MONITOR')
    return Monitor.objects.create(
        user=user,
        data_nascimento=datetime.date(1990, 7, 25),
        nrBI='777888999012E',
        salario='18000.00',
    )


class BaseAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='admin@test.com', password='Admin1234!',
            nome='Admin', role='ADMIN'
        )
        self.encarregado = make_encarregado()
        self.aluno       = make_aluno(encarregado=self.encarregado)
        self.motorista   = make_motorista()
        self.gestor      = make_gestor()
        self.monitor     = make_monitor()

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def unauth(self):
        self.client.force_authenticate(user=None)


class UserAPITest(BaseAPITest):

    def setUp(self):
        super().setUp()
        self.url_list   = reverse('core:user-list')
        self.url_me     = reverse('core:user-me')
        self.url_passwd = reverse('core:user-alterar-password')

    # ── autenticação ──

    def test_listar_users_sem_auth_retorna_401(self):
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_listar_users_admin_retorna_todos(self):
        self.auth(self.admin)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 5)

    def test_user_comum_so_ve_o_proprio(self):
        self.auth(self.aluno.user)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['email'], self.aluno.user.email)

    # ── me/ ──

    def test_me_retorna_utilizador_autenticado(self):
        self.auth(self.motorista.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.motorista.user.email)
        self.assertEqual(response.data['role'], 'MOTORISTA')

    def test_me_sem_auth_retorna_401(self):
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── criação ──

    def test_criar_user_valido(self):
        data = {
            'email': 'novo@test.com',
            'nome': 'Novo Utilizador',
            'role': 'ALUNO',
            'password': 'Senha1234!',
            'password2': 'Senha1234!',
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('password', response.data)

    def test_criar_user_passwords_diferentes_retorna_400(self):
        data = {
            'email': 'x@test.com', 'nome': 'X', 'role': 'ALUNO',
            'password': 'Senha1234!', 'password2': 'Outra1234!',
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password2', response.data)

    def test_criar_user_email_duplicado_retorna_400(self):
        data = {
            'email': self.aluno.user.email,
            'nome': 'Duplicado', 'role': 'ALUNO',
            'password': 'Senha1234!', 'password2': 'Senha1234!',
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_criar_user_password_curta_retorna_400(self):
        data = {
            'email': 'curta@test.com', 'nome': 'Curta', 'role': 'ALUNO',
            'password': '123', 'password2': '123',
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── alterar password ──

    def test_alterar_password_corretamente(self):
        self.auth(self.motorista.user)
        data = {
            'password_atual': 'Test1234!',
            'password_nova': 'NovaSenha99!',
            'password_nova2': 'NovaSenha99!',
        }
        response = self.client.post(self.url_passwd, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.motorista.user.refresh_from_db()
        self.assertTrue(self.motorista.user.check_password('NovaSenha99!'))

    def test_alterar_password_atual_errada_retorna_400(self):
        self.auth(self.motorista.user)
        data = {
            'password_atual': 'Errada123!',
            'password_nova': 'NovaSenha99!',
            'password_nova2': 'NovaSenha99!',
        }
        response = self.client.post(self.url_passwd, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_atual', response.data)

    # ── desativar ──

    def test_admin_pode_desativar_user(self):
        self.auth(self.admin)
        url = reverse('core:user-desativar', args=[self.aluno.user.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.aluno.user.refresh_from_db()
        self.assertFalse(self.aluno.user.is_active)

    def test_nao_admin_nao_pode_desativar_user(self):
        self.auth(self.gestor.user)
        url = reverse('core:user-desativar', args=[self.aluno.user.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AlunoAPITest(BaseAPITest):

    def setUp(self):
        super().setUp()
        self.url_list   = reverse('core:aluno-list')
        self.url_detail = reverse('core:aluno-detail', args=[self.aluno.pk])

    def test_admin_lista_todos_os_alunos(self):
        self.auth(self.admin)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_encarregado_so_ve_os_seus_alunos(self):
        outro_aluno = make_aluno(nome='Outro Aluno')
        self.auth(self.encarregado.user)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [a['email'] for a in response.data['results']]
        self.assertIn(self.aluno.user.email, emails)
        self.assertNotIn(outro_aluno.user.email, emails)

    def test_aluno_so_ve_o_proprio_perfil(self):
        self.auth(self.aluno.user)
        response = self.client.get(self.url_list)
        self.assertEqual(len(response.data['results']), 1)

    def test_criar_aluno_valido(self):
        self.auth(self.admin)
        data = {
            'email': 'novoaluno@test.com',
            'nome': 'Novo Aluno',
            'password': 'Senha1234!',
            'data_nascimento': '2012-03-10',
            'nrBI': '555666777012F',
            'escola_dest': 'Escola Norte',
            'classe': '3ª Classe',
            'mensalidade': '1200.00',
            'encarregado': self.encarregado.pk,
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_criar_aluno_data_nascimento_futura_retorna_400(self):
        self.auth(self.admin)
        data = {
            'email': 'futuro@test.com', 'nome': 'Futuro', 'password': 'Senha1234!',
            'data_nascimento': '2099-01-01', 'nrBI': '000111222012G',
            'escola_dest': 'Escola X', 'classe': '1ª', 'mensalidade': '0',
            'encarregado': self.encarregado.pk,
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_nascimento', response.data)

    def test_criar_aluno_menos_de_3_anos_retorna_400(self):
        self.auth(self.admin)
        bebe = (datetime.date.today() - datetime.timedelta(days=100)).isoformat()
        data = {
            'email': 'bebe@test.com', 'nome': 'Bebé', 'password': 'Senha1234!',
            'data_nascimento': bebe, 'nrBI': '000111333012H',
            'escola_dest': 'Escola X', 'classe': '1ª', 'mensalidade': '0',
            'encarregado': self.encarregado.pk,
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_detalhe_aluno_expoe_acesso_bloqueado(self):
        self.auth(self.admin)
        response = self.client.get(self.url_detail)
        self.assertIn('acesso_bloqueado', response.data)
        self.assertIsInstance(response.data['acesso_bloqueado'], bool)

    def test_detalhe_aluno_expoe_idade(self):
        self.auth(self.admin)
        response = self.client.get(self.url_detail)
        self.assertIn('idade', response.data)
        self.assertGreater(response.data['idade'], 0)

    def test_encarregado_acessa_rota_alunos(self):
        self.auth(self.encarregado.user)
        url = reverse('core:encarregado-alunos', args=[self.encarregado.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MotoristaAPITest(BaseAPITest):

    def setUp(self):
        super().setUp()
        self.url_list          = reverse('core:motorista-list')
        self.url_detail        = reverse('core:motorista-detail', args=[self.motorista.pk])
        self.url_carta_vencida = reverse('core:motorista-carta-vencida')
        self.url_me            = reverse('core:motorista-me')

    def test_listar_motoristas_autenticado(self):
        self.auth(self.admin)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detalhe_expoe_estado_carta(self):
        self.auth(self.admin)
        response = self.client.get(self.url_detail)
        self.assertIn('estado_carta', response.data)
        self.assertEqual(response.data['estado_carta'], 'valida')

    def test_estado_carta_vencida(self):
        self.auth(self.admin)
        self.motorista.validade_da_carta = datetime.date.today() - datetime.timedelta(days=1)
        self.motorista.save()
        response = self.client.get(self.url_detail)
        self.assertEqual(response.data['estado_carta'], 'vencida')
        self.assertTrue(response.data['carta_vencida'])

    def test_endpoint_carta_vencida(self):
        self.motorista.validade_da_carta = datetime.date.today() - datetime.timedelta(days=10)
        self.motorista.save()
        self.auth(self.admin)
        response = self.client.get(self.url_carta_vencida)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [m['email'] for m in response.data]
        self.assertIn(self.motorista.user.email, emails)

    def test_motorista_acede_ao_proprio_perfil_via_me(self):
        self.auth(self.motorista.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.motorista.user.email)

    def test_criar_motorista_carta_vencida_retorna_400(self):
        self.auth(self.admin)
        data = {
            'email': 'vencido@test.com', 'nome': 'Vencido', 'password': 'Senha1234!',
            'data_nascimento': '1985-01-01', 'nrBI': '321321321012Z',
            'carta_conducao': '987654321',
            'validade_da_carta': '2020-01-01',
            'salario': '20000.00',
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('validade_da_carta', response.data)

    def test_criar_motorista_menor_de_18_retorna_400(self):
        self.auth(self.admin)
        jovem = (datetime.date.today() - datetime.timedelta(days=365 * 16)).isoformat()
        data = {
            'email': 'jovem@test.com', 'nome': 'Jovem', 'password': 'Senha1234!',
            'data_nascimento': jovem, 'nrBI': '123123123012W',
            'carta_conducao': '111222333',
            'validade_da_carta': (datetime.date.today() + datetime.timedelta(days=365)).isoformat(),
            'salario': '20000.00',
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_nascimento', response.data)


class GestorAPITest(BaseAPITest):

    def setUp(self):
        super().setUp()
        self.url_list   = reverse('core:gestor-list')
        self.url_detail = reverse('core:gestor-detail', args=[self.gestor.pk])
        self.url_me     = reverse('core:gestor-me')

    def test_gestor_lista_todos_os_users(self):
        self.auth(self.gestor.user)
        response = self.client.get(reverse('core:user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 1)

    def test_detalhe_gestor_expoe_pode_aprovar(self):
        self.auth(self.admin)
        response = self.client.get(self.url_detail)
        self.assertIn('pode_aprovar_manutencao', response.data)
        self.assertIn('total_motoristas', response.data)

    def test_gestor_frota_pode_aprovar_manutencao(self):
        self.auth(self.admin)
        gestor_frota = make_gestor(nome='Gestor Frota', departamento='FROTA')
        url = reverse('core:gestor-detail', args=[gestor_frota.pk])
        response = self.client.get(url)
        self.assertTrue(response.data['pode_aprovar_manutencao'])

    def test_gestor_academico_nao_pode_aprovar_manutencao(self):
        self.auth(self.admin)
        gestor_ac = make_gestor(nome='Gestor Academico', departamento='ACADEMICO')
        url = reverse('core:gestor-detail', args=[gestor_ac.pk])
        response = self.client.get(url)
        self.assertFalse(response.data['pode_aprovar_manutencao'])

    def test_adicionar_motorista_a_gestor(self):
        self.auth(self.admin)
        url = reverse('core:gestor-adicionar-motorista', args=[self.gestor.pk])
        response = self.client.post(url, {'motorista_id': self.motorista.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.motorista, self.gestor.motoristas_supervisionados.all())

    def test_adicionar_motorista_duplicado_retorna_400(self):
        self.gestor.motoristas_supervisionados.add(self.motorista)
        self.auth(self.admin)
        url = reverse('core:gestor-adicionar-motorista', args=[self.gestor.pk])
        response = self.client.post(url, {'motorista_id': self.motorista.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remover_motorista_de_gestor(self):
        self.gestor.motoristas_supervisionados.add(self.motorista)
        self.auth(self.admin)
        url = reverse('core:gestor-remover-motorista', args=[self.gestor.pk])
        response = self.client.post(url, {'motorista_id': self.motorista.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.motorista, self.gestor.motoristas_supervisionados.all())

    def test_gestor_acede_ao_proprio_perfil_via_me(self):
        self.auth(self.gestor.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.gestor.user.email)


class MonitorAPITest(BaseAPITest):

    def setUp(self):
        super().setUp()
        self.url_list     = reverse('core:monitor-list')
        self.url_detail   = reverse('core:monitor-detail', args=[self.monitor.pk])
        self.url_sem_rota = reverse('core:monitor-sem-rota')
        self.url_me       = reverse('core:monitor-me')

    def test_listar_monitores_autenticado(self):
        self.auth(self.admin)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detalhe_monitor_expoe_rota_ativa_none(self):
        self.auth(self.admin)
        response = self.client.get(self.url_detail)
        self.assertIn('rota_ativa', response.data)
        self.assertIsNone(response.data['rota_ativa'])

    def test_endpoint_sem_rota_inclui_monitor_sem_rota(self):
        self.auth(self.admin)
        response = self.client.get(self.url_sem_rota)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [m['email'] for m in response.data]
        self.assertIn(self.monitor.user.email, emails)

    def test_rota_atual_sem_rota_retorna_404(self):
        self.auth(self.admin)
        url = reverse('core:monitor-rota-atual', args=[self.monitor.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_monitor_acede_ao_proprio_perfil_via_me(self):
        self.auth(self.monitor.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.monitor.user.email)

    def test_role_errado_nao_acede_a_me_monitor(self):
        """Um aluno não tem perfil de monitor — deve receber 404."""
        self.auth(self.aluno.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class EncarregadoAPITest(BaseAPITest):

    def setUp(self):
        super().setUp()
        self.url_list   = reverse('core:encarregado-list')
        self.url_detail = reverse('core:encarregado-detail', args=[self.encarregado.pk])
        self.url_alunos = reverse('core:encarregado-alunos', args=[self.encarregado.pk])
        self.url_me     = reverse('core:encarregado-me')

    def test_listar_encarregados_admin(self):
        self.auth(self.admin)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_encarregado_acede_aos_seus_alunos(self):
        self.auth(self.encarregado.user)
        response = self.client.get(self.url_alunos)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['email'], self.aluno.user.email)

    def test_encarregado_acede_ao_proprio_perfil_via_me(self):
        self.auth(self.encarregado.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.encarregado.user.email)

    def test_outro_encarregado_nao_acede_aos_alunos_alheios(self):
        outro = make_encarregado(nome='Outro Encarregado')
        self.auth(outro.user)
        response = self.client.get(self.url_alunos)
        # Ou 403 ou lista vazia — depende da implementação
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(len(response.data), 0)
        else:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_criar_encarregado_valido(self):
        self.auth(self.admin)
        data = {
            'email': 'enc2@test.com',
            'nome': 'Novo Encarregado',
            'password': 'Senha1234!',
            'nrBI': '222333444012X',
            'telefone': '+258841111222',
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('password', response.data)

# from rest_framework.test import APITestCase
# from rest_framework import status
# from django.urls import reverse
# from accounts.models import User
# from core.models import Aluno, Motorista, Encarregado
# from datetime import date, timedelta

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

#         # Criar perfis
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

#     def test_admin_can_list_alunos(self):
#         self.client.login(email="admin@test.com", password="senha1234")
#         url = reverse("core:aluno-list")
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertGreaterEqual(len(response.data), 1)

#     def test_motorista_can_only_see_self(self):
#         self.client.login(email="motorista@test.com", password="senha1234")
#         url = reverse("core:motorista-list")
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 1)
#         self.assertEqual(response.data[0]["email"], "motorista@test.com")

#     def test_encarregado_sees_only_children(self):
#         self.client.login(email="encarregado@test.com", password="senha1234")
#         url = reverse("core:aluno-list")
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 1)
#         self.assertEqual(response.data[0]["email"], "aluno@test.com")

#     def test_aluno_sees_only_self(self):
#         self.client.login(email="aluno@test.com", password="senha1234")
#         url = reverse("core:aluno-list")
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 1)
#         self.assertEqual(response.data[0]["email"], "aluno@test.com")
