"""
tests/core/test_models.py
=========================
Testes de modelos e signals do módulo core.

Executar:
    python manage.py test tests.core.test_models
    python manage.py test tests.core.test_models.UserManagerTests
    python manage.py test tests.core.test_models.UserManagerTests.test_criar_user_normal
"""

import datetime
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from tests.factories import (
    criar_aluno,
    criar_encarregado,
    criar_gestor,
    criar_mensalidade,
    criar_monitor,
    criar_motorista,
    criar_user,
    criar_veiculo,
    data_futura,
    data_nascimento_adulto,
    data_nascimento_aluno,
    data_passada,
)


class UserManagerTests(TestCase):

    def test_criar_user_normal(self):
        from core.models import User
        u = User.objects.create_user(
            email='test@teste.co.mz',
            password='Senha@1234',
            nome='Ana Silva',
            role='GESTOR',
        )
        self.assertEqual(u.email, 'test@teste.co.mz')
        self.assertEqual(u.nome, 'Ana Silva')
        self.assertTrue(u.check_password('Senha@1234'))
        self.assertFalse(u.is_staff)

    def test_email_normalizado_para_minusculas(self):
        from core.models import User
        u = User.objects.create_user(
            email='TEST@TESTE.CO.MZ',
            password='Senha@1234',
            nome='João',
            role='GESTOR',
        )
        self.assertEqual(u.email, 'test@teste.co.mz')

    def test_criar_user_sem_email_levanta_erro(self):
        from core.models import User
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='x', nome='X', role='GESTOR')

    def test_criar_user_sem_nome_levanta_erro(self):
        from core.models import User
        with self.assertRaises(ValueError):
            User.objects.create_user(email='a@b.com', password='x', nome='', role='GESTOR')

    def test_criar_user_sem_role_levanta_erro(self):
        from core.models import User
        with self.assertRaises(ValueError):
            User.objects.create_user(email='a@b.com', password='x', nome='X', role='')

    def test_criar_superuser(self):
        from core.models import User
        u = User.objects.create_superuser(
            email='admin@teste.co.mz',
            password='Admin@1234',
        )
        self.assertTrue(u.is_staff)
        self.assertTrue(u.is_superuser)
        self.assertEqual(u.role, 'ADMIN')

    def test_email_unico(self):
        from django.db import IntegrityError
        criar_user(email='unico@teste.co.mz')
        with self.assertRaises(IntegrityError):
            criar_user(email='unico@teste.co.mz')


class UserModelTests(TestCase):

    def test_nome_curto_retorna_primeiro_nome(self):
        u = criar_user(nome='Maria João Silva')
        self.assertEqual(u.nome_curto, 'Maria')

    def test_nome_curto_com_nome_simples(self):
        u = criar_user(nome='Carlos')
        self.assertEqual(u.nome_curto, 'Carlos')

    def test_str_contem_nome_e_role(self):
        u = criar_user(role='GESTOR', nome='Pedro Costa')
        self.assertIn('Pedro Costa', str(u))
        self.assertIn('Gestor', str(u))

    def test_is_active_default_true(self):
        u = criar_user()
        self.assertTrue(u.is_active)


class EncarregadoModelTests(TestCase):

    def test_criar_encarregado_valido(self):
        enc = criar_encarregado()
        self.assertIsNotNone(enc.pk)
        self.assertEqual(enc.user.role, 'ENCARREGADO')

    def test_clean_role_errado_levanta_erro(self):
        from core.models import Encarregado
        u = criar_user(role='GESTOR')
        enc = Encarregado(
            user=u,
            data_nascimento=data_nascimento_adulto(),
            nrBI='000000000001A',
        )
        with self.assertRaises(ValidationError):
            enc.clean()

    def test_str_contem_encarregado(self):
        enc = criar_encarregado()
        self.assertIn('Encarregado', str(enc))

    def test_data_nascimento_futura_levanta_erro(self):
        from core.models import Encarregado
        u = criar_user(role='ENCARREGADO')
        enc = Encarregado(
            user=u,
            data_nascimento=data_futura(10),
            nrBI='000000000002A',
        )
        with self.assertRaises(ValidationError):
            enc.full_clean()


class AlunoModelTests(TestCase):

    def test_criar_aluno_valido(self):
        aluno = criar_aluno()
        self.assertIsNotNone(aluno.pk)
        self.assertEqual(aluno.user.role, 'ALUNO')

    def test_aluno_muito_novo_levanta_erro(self):
        from core.models import Aluno
        enc = criar_encarregado()
        u = criar_user(role='ALUNO')
        nasc = datetime.date.today() - datetime.timedelta(days=365)
        aluno = Aluno(
            user=u, encarregado=enc,
            data_nascimento=nasc,
            nrBI='000000000003A',
            escola_dest='Escola X', classe='1ª',
            mensalidade=Decimal('1000.00'),
        )
        with self.assertRaises(ValidationError):
            aluno.full_clean()

    def test_aluno_com_role_errado_levanta_erro(self):
        from core.models import Aluno
        enc = criar_encarregado()
        u = criar_user(role='GESTOR')
        aluno = Aluno(
            user=u, encarregado=enc,
            data_nascimento=data_nascimento_aluno(),
            nrBI='000000000004A',
            escola_dest='Escola X', classe='5ª',
            mensalidade=Decimal('1000.00'),
        )
        with self.assertRaises(ValidationError):
            aluno.clean()

    def test_propriedade_idade(self):
        hoje = datetime.date.today()
        nasc = hoje.replace(year=hoje.year - 12)
        aluno = criar_aluno(data_nascimento=nasc)
        self.assertEqual(aluno.idade, 12)

    def test_str_contem_aluno(self):
        self.assertIn('Aluno', str(criar_aluno()))


class MotoristaModelTests(TestCase):

    def test_criar_motorista_valido(self):
        self.assertIsNotNone(criar_motorista().pk)

    def test_carta_conducao_vencida_retorna_true(self):
        from core.models import Motorista
        m = criar_motorista()
        Motorista.objects.filter(pk=m.pk).update(validade_da_carta=data_passada(10))
        m.refresh_from_db()
        self.assertTrue(m.carta_conducao_vencida())

    def test_carta_conducao_valida_retorna_false(self):
        m = criar_motorista(validade_da_carta=data_futura(100))
        self.assertFalse(m.carta_conducao_vencida())

    def test_clean_carta_vencida_levanta_erro(self):
        from core.models import Motorista
        u = criar_user(role='MOTORISTA')
        m = Motorista(
            user=u,
            data_nascimento=data_nascimento_adulto(),
            nrBI='000000000005A',
            carta_conducao='123456789',
            validade_da_carta=data_passada(10),
            salario=Decimal('15000.00'),
        )
        with self.assertRaises(ValidationError):
            m.clean()

    def test_motorista_menor_de_18_levanta_erro(self):
        from core.models import Motorista
        u = criar_user(role='MOTORISTA')
        hoje = datetime.date.today()
        m = Motorista(
            user=u,
            data_nascimento=hoje.replace(year=hoje.year - 16),
            nrBI='000000000006A',
            carta_conducao='987654321',
            validade_da_carta=data_futura(365),
            salario=Decimal('15000.00'),
        )
        with self.assertRaises(ValidationError):
            m.clean()

    def test_str_contem_motorista(self):
        self.assertIn('Motorista', str(criar_motorista()))


class GestorModelTests(TestCase):

    def test_criar_gestor_valido(self):
        self.assertIsNotNone(criar_gestor().pk)

    def test_pode_aprovar_manutencao_frota(self):
        self.assertTrue(criar_gestor(departamento='FROTA').pode_aprovar_manutencao())

    def test_nao_pode_aprovar_manutencao_academico(self):
        self.assertFalse(criar_gestor(departamento='ACADEMICO').pode_aprovar_manutencao())

    def test_pode_aprovar_abastecimento_geral(self):
        self.assertTrue(criar_gestor(departamento='GERAL').pode_aprovar_abastecimento())

    def test_str_contem_gestor(self):
        self.assertIn('Gestor', str(criar_gestor()))


class MonitorModelTests(TestCase):

    def test_criar_monitor_valido(self):
        self.assertIsNotNone(criar_monitor().pk)

    def test_tem_rota_ativa_false_sem_rota(self):
        self.assertFalse(criar_monitor().tem_rota_ativa())

    def test_str_contem_monitor(self):
        self.assertIn('Monitor', str(criar_monitor()))


class SignalCriarPerfilTests(TestCase):

    def test_user_motorista_cria_perfil_automaticamente(self):
        from core.models import Motorista
        u = criar_user(role='MOTORISTA')
        self.assertTrue(Motorista.objects.filter(user=u).exists())

    def test_user_monitor_cria_perfil_automaticamente(self):
        from core.models import Monitor
        u = criar_user(role='MONITOR')
        self.assertTrue(Monitor.objects.filter(user=u).exists())

    def test_user_gestor_cria_perfil_automaticamente(self):
        from core.models import Gestor
        u = criar_user(role='GESTOR')
        self.assertTrue(Gestor.objects.filter(user=u).exists())

    def test_user_admin_nao_cria_perfil_extra(self):
        from core.models import Gestor, Monitor, Motorista
        u = criar_user(role='ADMIN')
        self.assertFalse(Motorista.objects.filter(user=u).exists())
        self.assertFalse(Monitor.objects.filter(user=u).exists())
        self.assertFalse(Gestor.objects.filter(user=u).exists())


class SignalDesactivarPerfilTests(TestCase):

    def test_desactivar_user_motorista_desactiva_perfil(self):
        m = criar_motorista()
        m.user.is_active = False
        m.user.save()
        m.refresh_from_db()
        self.assertFalse(m.ativo)

    def test_desactivar_user_gestor_desactiva_perfil(self):
        from core.models import Gestor
        u = criar_user(role='GESTOR')
        g = Gestor.objects.get(user=u)
        g.data_nascimento = data_nascimento_adulto()
        g.nrBI = '123456789012A'
        g.save()
        u.is_active = False
        u.save()
        g.refresh_from_db()
        self.assertFalse(g.ativo)


class SignalBloquearDeleteMotoristaTests(TestCase):

    def test_delete_motorista_com_veiculo_levanta_permissao_negada(self):
        m = criar_motorista()
        criar_veiculo(motorista=m)
        with self.assertRaises(PermissionDenied):
            m.delete()

    def test_delete_motorista_sem_veiculo_permitido(self):
        criar_motorista().delete()  # não deve levantar excepção


class SignalBloquearDeleteAlunoTests(TestCase):

    def setUp(self):
        from tests.factories import criar_config_financeira
        criar_config_financeira()

    def test_delete_aluno_com_mensalidade_levanta_permissao_negada(self):
        aluno = criar_aluno()
        criar_mensalidade(aluno=aluno)
        with self.assertRaises(PermissionDenied):
            aluno.delete()

    def test_delete_aluno_sem_historico_permitido(self):
        criar_aluno().delete()  # não deve levantar excepção
