"""
core/tests/test_core.py
"""

import datetime
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse

from core.models import Aluno, Encarregado, Motorista, Gestor, Monitor

User = get_user_model()


def make_user(email, nome, role, password='Test1234!', **kwargs):
    return User.objects.create_user(
        email=email, nome=nome, role=role, password=password, **kwargs
    )

def make_encarregado(sufixo='1'):
    user = make_user(f'enc{sufixo}@test.com', f'Encarregado {sufixo}', 'ENCARREGADO')
    return Encarregado.objects.create(
        user=user,
        data_nascimento=datetime.date(1980, 1, 1),
        nrBI=f'10000000000{sufixo}A',
        telefone=f'+25884000000{sufixo}',
    )

def make_aluno(encarregado=None, sufixo='1'):
    if encarregado is None:
        encarregado = make_encarregado(sufixo='e' + sufixo)
    user = make_user(f'aluno{sufixo}@test.com', f'Aluno {sufixo}', 'ALUNO')
    return Aluno.objects.create(
        user=user,
        encarregado=encarregado,
        data_nascimento=datetime.date(2012, 5, 10),
        nrBI=f'20000000000{sufixo}B',
        escola_dest='Escola Central',
        classe='5ª Classe',
        mensalidade=Decimal('1500.00'),
    )

def make_motorista(sufixo='1'):
    user = make_user(f'mot{sufixo}@test.com', f'Motorista {sufixo}', 'MOTORISTA')
    return Motorista.objects.create(
        user=user,
        data_nascimento=datetime.date(1985, 3, 20),
        nrBI=f'30000000000{sufixo}C',
        carta_conducao=f'10000000{sufixo}',
        validade_da_carta=datetime.date.today() + datetime.timedelta(days=365),
        salario=Decimal('25000.00'),
    )

def make_gestor(sufixo='1', departamento='GERAL'):
    user = make_user(f'gest{sufixo}@test.com', f'Gestor {sufixo}', 'GESTOR')
    return Gestor.objects.create(
        user=user,
        data_nascimento=datetime.date(1978, 6, 15),
        nrBI=f'40000000000{sufixo}D',
        departamento=departamento,
        salario=Decimal('40000.00'),
    )

def make_monitor(sufixo='1'):
    user = make_user(f'mon{sufixo}@test.com', f'Monitor {sufixo}', 'MONITOR')
    return Monitor.objects.create(
        user=user,
        data_nascimento=datetime.date(1992, 9, 5),
        nrBI=f'50000000000{sufixo}E',
        salario=Decimal('18000.00'),
    )


class BaseTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin@test.com', password='Admin1234!',
            nome='Administrador',
        )
        self.encarregado = make_encarregado()
        self.aluno = make_aluno(encarregado=self.encarregado)
        self.motorista = make_motorista()
        self.gestor = make_gestor()
        self.monitor = make_monitor()

class BaseAPITestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def unauth(self):
        self.client.force_authenticate(user=None)


class TestUserModel(BaseTestCase):

    def test_create_user_normaliza_email(self):
        user = make_user('TESTE@TEST.COM', 'Teste', 'ALUNO')
        self.assertEqual(user.email, 'teste@test.com')

    def test_create_user_capitaliza_nome(self):
        user = make_user('cap@test.com', 'joao silva', 'ALUNO')
        self.assertEqual(user.nome, 'João Silva')

    def test_create_user_sem_email_levanta_erro(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', nome='X', role='ALUNO', password='Test1234!')

    def test_create_user_sem_nome_levanta_erro(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='x@test.com', nome='', role='ALUNO', password='Test1234!')

    def test_create_user_sem_role_levanta_erro(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='x@test.com', nome='X', role='', password='Test1234!')

    def test_create_user_password_curta_levanta_erro(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='x@test.com', nome='X', role='ALUNO', password='123')

    def test_create_superuser_defaults(self):
        su = User.objects.create_superuser(email='su@test.com', password='Admin1234!')
        self.assertTrue(su.is_staff)
        self.assertTrue(su.is_superuser)
        self.assertEqual(su.role, 'ADMIN')

    def test_nome_curto_devolve_primeiro_nome(self):
        self.assertEqual(self.admin.nome_curto, 'Administrador')

    def test_str_format(self):
        self.assertIn(self.admin.email, str(self.admin))
        self.assertIn('Administrador', str(self.admin))

    def test_roles_disponiveis(self):
        roles = [c.value for c in User.Cargo]
        for r in ['ADMIN', 'GESTOR', 'MOTORISTA', 'MONITOR', 'ENCARREGADO', 'ALUNO']:
            self.assertIn(r, roles)


class TestEncarregadoModel(BaseTestCase):

    def test_criacao_valida(self):
        self.assertEqual(self.encarregado.user.role, 'ENCARREGADO')
        self.assertTrue(self.encarregado.ativo)

    def test_role_errado_levanta_erro(self):
        user = make_user('errado@test.com', 'Errado', 'ALUNO')
        enc = Encarregado(
            user=user,
            data_nascimento=datetime.date(1980, 1, 1),
            nrBI='99999999999ZA',
        )
        with self.assertRaises(ValidationError):
            enc.full_clean()

    def test_str_contem_nome(self):
        self.assertIn(self.encarregado.user.nome, str(self.encarregado))


class TestAlunoModel(BaseTestCase):

    def test_idade_calculada_corretamente(self):
        self.assertGreater(self.aluno.idade, 0)

    def test_data_nascimento_futura_levanta_erro(self):
        aluno = Aluno(
            user=make_user('fut@test.com', 'Futuro', 'ALUNO'),
            encarregado=self.encarregado,
            data_nascimento=datetime.date.today() + datetime.timedelta(days=1),
            nrBI='88888888888ZB',
            escola_dest='X', classe='1ª',
        )
        with self.assertRaises(ValidationError):
            aluno.full_clean()

    def test_aluno_menos_3_anos_levanta_erro(self):
        aluno = Aluno(
            user=make_user('bebe@test.com', 'Bebé', 'ALUNO'),
            encarregado=self.encarregado,
            data_nascimento=datetime.date.today() - datetime.timedelta(days=200),
            nrBI='77777777777ZC',
            escola_dest='X', classe='1ª',
        )
        with self.assertRaises(ValidationError):
            aluno.full_clean()

    def test_tem_acesso_bloqueado_falso_sem_transacoes(self):
        self.assertFalse(self.aluno.tem_acesso_bloqueado())

    def test_role_errado_levanta_erro(self):
        user = make_user('wrong@test.com', 'Wrong', 'MOTORISTA')
        aluno = Aluno(
            user=user, encarregado=self.encarregado,
            data_nascimento=datetime.date(2012, 1, 1),
            nrBI='66666666666ZD', escola_dest='X', classe='1ª',
        )
        with self.assertRaises(ValidationError):
            aluno.full_clean()


class TestMotoristaModel(BaseTestCase):

    def test_carta_valida(self):
        self.assertFalse(self.motorista.carta_conducao_vencida())

    def test_carta_vencida(self):
        self.motorista.validade_da_carta = datetime.date.today() - datetime.timedelta(days=1)
        self.motorista.save()
        self.assertTrue(self.motorista.carta_conducao_vencida())

    def test_sem_data_carta_considerada_vencida(self):
        m = Motorista(
            user=make_user('sdm@test.com', 'Sem Data', 'MOTORISTA'),
            data_nascimento=datetime.date(1985, 1, 1),
            nrBI='55555555555ZE',
            carta_conducao='555555555',
            validade_da_carta=None,
            salario=Decimal('0'),
        )
        self.assertTrue(m.carta_conducao_vencida())

    def test_idade_calculada(self):
        self.assertGreaterEqual(self.motorista.idade, 18)

    def test_motorista_menor_18_levanta_erro(self):
        m = Motorista(
            user=make_user('jovem@test.com', 'Jovem', 'MOTORISTA'),
            data_nascimento=datetime.date.today() - datetime.timedelta(days=365 * 16),
            nrBI='44444444444ZF',
            carta_conducao='444444444',
            validade_da_carta=datetime.date.today() + datetime.timedelta(days=365),
            salario=Decimal('0'),
        )
        with self.assertRaises(ValidationError):
            m.full_clean()

    def test_carta_expirada_levanta_erro_no_clean(self):
        m = Motorista(
            user=make_user('exp@test.com', 'Expirado', 'MOTORISTA'),
            data_nascimento=datetime.date(1985, 1, 1),
            nrBI='33333333333ZG',
            carta_conducao='333333333',
            validade_da_carta=datetime.date(2020, 1, 1),
            salario=Decimal('0'),
        )
        with self.assertRaises(ValidationError):
            m.full_clean()


class TestGestorModel(BaseTestCase):

    def test_gestor_geral_pode_aprovar_manutencao(self):
        self.assertTrue(self.gestor.pode_aprovar_manutencao())

    def test_gestor_frota_pode_aprovar_manutencao(self):
        g = make_gestor(sufixo='f', departamento='FROTA')
        self.assertTrue(g.pode_aprovar_manutencao())

    def test_gestor_academico_nao_pode_aprovar_manutencao(self):
        g = make_gestor(sufixo='a', departamento='ACADEMICO')
        self.assertFalse(g.pode_aprovar_manutencao())

    def test_gestor_financeiro_nao_pode_aprovar_manutencao(self):
        g = make_gestor(sufixo='fi', departamento='FINANCEIRO')
        self.assertFalse(g.pode_aprovar_manutencao())

    def test_gestor_inativo_nao_pode_aprovar(self):
        self.gestor.ativo = False
        self.gestor.save()
        self.assertFalse(self.gestor.pode_aprovar_manutencao())

    def test_adicionar_motorista_supervisionado(self):
        self.gestor.motoristas_supervisionados.add(self.motorista)
        self.assertIn(self.motorista, self.gestor.motoristas_supervisionados.all())

    def test_role_errado_levanta_erro(self):
        user = make_user('gw@test.com', 'GWrong', 'ALUNO')
        g = Gestor(
            user=user, data_nascimento=datetime.date(1980, 1, 1),
            nrBI='22222222222ZH', departamento='GERAL',
        )
        with self.assertRaises(ValidationError):
            g.full_clean()


class TestMonitorModel(BaseTestCase):

    def test_sem_rota_rota_ativa_none(self):
        self.assertIsNone(self.monitor.rota_ativa)

    def test_sem_rota_tem_rota_ativa_false(self):
        self.assertFalse(self.monitor.tem_rota_ativa())

    def test_role_errado_levanta_erro(self):
        user = make_user('mw@test.com', 'MWrong', 'ALUNO')
        m = Monitor(
            user=user, data_nascimento=datetime.date(1990, 1, 1),
            nrBI='11111111111ZI', salario=Decimal('0'),
        )
        with self.assertRaises(ValidationError):
            m.full_clean()

    def test_monitor_menor_18_levanta_erro(self):
        m = Monitor(
            user=make_user('mj@test.com', 'MJovem', 'MONITOR'),
            data_nascimento=datetime.date.today() - datetime.timedelta(days=365 * 16),
            nrBI='00000000000ZJ',
            salario=Decimal('0'),
        )
        with self.assertRaises(ValidationError):
            m.full_clean()


class TestUserAPI(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.url_list = reverse('core:user-list')
        self.url_me = reverse('core:user-me')
        self.url_passwd = reverse('core:user-alterar-password')

    def test_listar_sem_auth_retorna_401(self):
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_lista_todos(self):
        self.auth(self.admin)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 5)

    def test_gestor_lista_todos(self):
        self.auth(self.gestor.user)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data['count'], 1)

    def test_aluno_so_ve_o_proprio(self):
        self.auth(self.aluno.user)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['email'], self.aluno.user.email)

    def test_me_retorna_user_autenticado(self):
        self.auth(self.motorista.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.motorista.user.email)
        self.assertEqual(response.data['role'], 'MOTORISTA')

    def test_criar_user_valido(self):
        data = {
            'email': 'novo@test.com', 'nome': 'Novo',
            'role': 'ALUNO', 'password': 'Senha1234!', 'password2': 'Senha1234!',
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
            'email': self.aluno.user.email, 'nome': 'Dup',
            'role': 'ALUNO', 'password': 'Senha1234!', 'password2': 'Senha1234!',
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_alterar_password_com_sucesso(self):
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

    def test_admin_desativa_user(self):
        self.auth(self.admin)
        url = reverse('core:user-desativar', args=[self.aluno.user.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.aluno.user.refresh_from_db()
        self.assertFalse(self.aluno.user.is_active)

    def test_nao_admin_nao_pode_desativar(self):
        self.auth(self.gestor.user)
        url = reverse('core:user-desativar', args=[self.aluno.user.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestEncarregadoAPI(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.url_list = reverse('core:encarregado-list')
        self.url_me = reverse('core:encarregado-me')
        self.url_alunos = reverse('core:encarregado-alunos', args=[self.encarregado.pk])

    def test_admin_lista_encarregados(self):
        self.auth(self.admin)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_encarregado_acede_ao_proprio_me(self):
        self.auth(self.encarregado.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.encarregado.user.email)

    def test_encarregado_lista_os_seus_alunos(self):
        self.auth(self.encarregado.user)
        response = self.client.get(self.url_alunos)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [a['email'] for a in response.data]
        self.assertIn(self.aluno.user.email, emails)

    def test_outro_encarregado_nao_ve_alunos_alheios(self):
        outro = make_encarregado(sufixo='2')
        self.auth(outro.user)
        response = self.client.get(self.url_alunos)
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(len(response.data), 0)
        else:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_criar_encarregado_valido(self):
        self.auth(self.admin)
        data = {
            'email': 'enc99@test.com', 'nome': 'Enc Novo',
            'password': 'Senha1234!',
            'data_nascimento': '1982-04-10',
            'nrBI': '600000000001A',
            'telefone': '+258841111999',
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('password', response.data)

    def test_criar_encarregado_sem_auth_retorna_403(self):
        response = self.client.post(self.url_list, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestAlunoAPI(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.url_list = reverse('core:aluno-list')
        self.url_detail = reverse('core:aluno-detail', args=[self.aluno.pk])
        self.url_me = reverse('core:aluno-me')
        self.url_bloqueado = reverse('core:aluno-acesso-bloqueado')

    def test_admin_lista_todos_alunos(self):
        self.auth(self.admin)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_encarregado_so_ve_os_seus_alunos(self):
        outro_aluno = make_aluno(sufixo='x')
        self.auth(self.encarregado.user)
        response = self.client.get(self.url_list)
        emails = [a['email'] for a in response.data['results']]
        self.assertIn(self.aluno.user.email, emails)
        self.assertNotIn(outro_aluno.user.email, emails)

    def test_aluno_so_ve_o_proprio_perfil(self):
        self.auth(self.aluno.user)
        response = self.client.get(self.url_list)
        self.assertEqual(response.data['count'], 1)

    def test_detalhe_expoe_acesso_bloqueado(self):
        self.auth(self.admin)
        response = self.client.get(self.url_detail)
        self.assertIn('acesso_bloqueado', response.data)
        self.assertIsInstance(response.data['acesso_bloqueado'], bool)

    def test_detalhe_expoe_idade(self):
        self.auth(self.admin)
        response = self.client.get(self.url_detail)
        self.assertIn('idade', response.data)
        self.assertGreater(response.data['idade'], 0)

    def test_criar_aluno_valido(self):
        self.auth(self.admin)
        data = {
            'email': 'alunox@test.com', 'nome': 'Aluno X',
            'password': 'Senha1234!',
            'data_nascimento': '2012-06-01',
            'nrBI': '700000000001F',
            'escola_dest': 'Escola Norte',
            'classe': '3ª Classe',
            'mensalidade': '1200.00',
            'encarregado': self.encarregado.pk,
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_criar_aluno_data_futura_retorna_400(self):
        self.auth(self.admin)
        data = {
            'email': 'fut@test.com', 'nome': 'Fut', 'password': 'Senha1234!',
            'data_nascimento': '2099-01-01', 'nrBI': '800000000001G',
            'escola_dest': 'X', 'classe': '1ª', 'mensalidade': '0',
            'encarregado': self.encarregado.pk,
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_nascimento', str(response.data))

    def test_criar_aluno_menos_3_anos_retorna_400(self):
        self.auth(self.admin)
        bebe = (datetime.date.today() - datetime.timedelta(days=200)).isoformat()
        data = {
            'email': 'bebe@test.com', 'nome': 'Bebé', 'password': 'Senha1234!',
            'data_nascimento': bebe, 'nrBI': '900000000001H',
            'escola_dest': 'X', 'classe': '1ª', 'mensalidade': '0',
            'encarregado': self.encarregado.pk,
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_endpoint_acesso_bloqueado_acessivel_por_admin(self):
        self.auth(self.admin)
        response = self.client.get(self.url_bloqueado)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_endpoint_acesso_bloqueado_bloqueado_para_aluno(self):
        self.auth(self.aluno.user)
        response = self.client.get(self.url_bloqueado)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestMotoristaAPI(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.url_list = reverse('core:motorista-list')
        self.url_detail = reverse('core:motorista-detail', args=[self.motorista.pk])
        self.url_me = reverse('core:motorista-me')
        self.url_carta = reverse('core:motorista-carta-vencida')

    def test_admin_lista_motoristas(self):
        self.auth(self.admin)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detalhe_expoe_estado_carta_valida(self):
        self.auth(self.admin)
        response = self.client.get(self.url_detail)
        self.assertEqual(response.data['estado_carta'], 'valida')
        self.assertFalse(response.data['carta_vencida'])

    def test_estado_carta_vencida(self):
        self.motorista.validade_da_carta = datetime.date.today() - datetime.timedelta(days=1)
        self.motorista.save()
        self.auth(self.admin)
        response = self.client.get(self.url_detail)
        self.assertEqual(response.data['estado_carta'], 'vencida')
        self.assertTrue(response.data['carta_vencida'])

    def test_estado_carta_expira_em_breve(self):
        self.motorista.validade_da_carta = datetime.date.today() + datetime.timedelta(days=15)
        self.motorista.save()
        self.auth(self.admin)
        response = self.client.get(self.url_detail)
        self.assertEqual(response.data['estado_carta'], 'expira_em_breve')

    def test_endpoint_carta_vencida_lista_vencidos(self):
        self.motorista.validade_da_carta = datetime.date.today() - datetime.timedelta(days=5)
        self.motorista.save()
        self.auth(self.admin)
        response = self.client.get(self.url_carta)
        emails = [m['email'] for m in response.data]
        self.assertIn(self.motorista.user.email, emails)

    def test_motorista_acede_ao_proprio_me(self):
        self.auth(self.motorista.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.motorista.user.email)

    def test_criar_motorista_carta_vencida_retorna_400(self):
        self.auth(self.admin)
        data = {
            'email': 'mv@test.com', 'nome': 'Mv', 'password': 'Senha1234!',
            'data_nascimento': '1985-01-01', 'nrBI': '111111111001Z',
            'carta_conducao': '111111111',
            'validade_da_carta': '2020-01-01',
            'salario': '20000.00',
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('validade_da_carta', response.data)

    def test_criar_motorista_menor_18_retorna_400(self):
        self.auth(self.admin)
        jovem = (datetime.date.today() - datetime.timedelta(days=365 * 16)).isoformat()
        data = {
            'email': 'mj@test.com', 'nome': 'Mj', 'password': 'Senha1234!',
            'data_nascimento': jovem, 'nrBI': '222222222001Y',
            'carta_conducao': '222222222',
            'validade_da_carta': (datetime.date.today() + datetime.timedelta(days=365)).isoformat(),
            'salario': '20000.00',
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_nascimento', str(response.data))


class TestGestorAPI(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.url_list = reverse('core:gestor-list')
        self.url_detail = reverse('core:gestor-detail', args=[self.gestor.pk])
        self.url_me = reverse('core:gestor-me')
        self.url_add = reverse('core:gestor-adicionar-motorista', args=[self.gestor.pk])
        self.url_rem = reverse('core:gestor-remover-motorista', args=[self.gestor.pk])

    def test_admin_lista_gestores(self):
        self.auth(self.admin)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detalhe_expoe_pode_aprovar_e_total_motoristas(self):
        self.auth(self.admin)
        response = self.client.get(self.url_detail)
        self.assertIn('pode_aprovar_manutencao', response.data)
        self.assertIn('total_motoristas', response.data)
        self.assertTrue(response.data['pode_aprovar_manutencao'])  # GERAL
        self.assertEqual(response.data['total_motoristas'], 0)

    def test_gestor_academico_nao_pode_aprovar(self):
        g = make_gestor(sufixo='ac2', departamento='ACADEMICO')
        self.auth(self.admin)
        url = reverse('core:gestor-detail', args=[g.pk])
        response = self.client.get(url)
        self.assertFalse(response.data['pode_aprovar_manutencao'])

    def test_adicionar_motorista(self):
        self.auth(self.admin)
        response = self.client.post(self.url_add, {'motorista_id': self.motorista.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.motorista, self.gestor.motoristas_supervisionados.all())

    def test_adicionar_motorista_duplicado_retorna_400(self):
        self.gestor.motoristas_supervisionados.add(self.motorista)
        self.auth(self.admin)
        response = self.client.post(self.url_add, {'motorista_id': self.motorista.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remover_motorista(self):
        self.gestor.motoristas_supervisionados.add(self.motorista)
        self.auth(self.admin)
        response = self.client.post(self.url_rem, {'motorista_id': self.motorista.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.motorista, self.gestor.motoristas_supervisionados.all())

    def test_gestor_acede_ao_proprio_me(self):
        self.auth(self.gestor.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.gestor.user.email)


class TestMonitorAPI(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.url_list = reverse('core:monitor-list')
        self.url_detail = reverse('core:monitor-detail', args=[self.monitor.pk])
        self.url_me = reverse('core:monitor-me')
        self.url_sem_rota = reverse('core:monitor-sem-rota')
        self.url_rota_atual = reverse('core:monitor-rota-atual', args=[self.monitor.pk])

    def test_admin_lista_monitores(self):
        self.auth(self.admin)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detalhe_expoe_rota_ativa_none(self):
        self.auth(self.admin)
        response = self.client.get(self.url_detail)
        self.assertIn('rota_ativa', response.data)
        self.assertIsNone(response.data['rota_ativa'])

    def test_endpoint_sem_rota_inclui_monitor(self):
        self.auth(self.admin)
        response = self.client.get(self.url_sem_rota)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [m['email'] for m in response.data]
        self.assertIn(self.monitor.user.email, emails)

    def test_rota_atual_sem_rota_retorna_404(self):
        self.auth(self.admin)
        response = self.client.get(self.url_rota_atual)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_monitor_acede_ao_proprio_me(self):
        self.auth(self.monitor.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.monitor.user.email)

    def test_role_errado_me_retorna_404(self):
        """Aluno não tem perfil de monitor — deve receber 404."""
        self.auth(self.aluno.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_sem_rota_bloqueado_para_motorista(self):
        self.auth(self.motorista.user)
        response = self.client.get(self.url_sem_rota)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
