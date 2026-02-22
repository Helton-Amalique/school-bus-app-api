"""Teste para os modelos do aplicativo"""

from django.test import TestCase
from accounts.models import User
from decimal import Decimal
from datetime import timedelta, date
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from core.models import Aluno, Encarregado, Motorista

validador_carta = RegexValidator(
    regex=r'^\d{9}$',
    message="Formato inválido para carta de condução. Use 9 dígitos."
)


class EncarregadoModelTest(TestCase):

    def test_criar_encarregado_sucesso(self):
        user = User.objects.create_user(
            email="encarregado@exemplo.com",
            nome="Calos Martins",
            role=User.Cargo.ENCARREGADO,
            password="senha123"
        )
        encarregado = Encarregado.objects.create(
            user=user,
            telefone="+258821234500",
            endereco="Rua Teste, 123"
        )
        self.assertEqual(encarregado.user.role, user.Cargo.ENCARREGADO)
        self.assertEqual(str(encarregado), f"Encarregado: {user.nome} - {user.email}")


class AlunoModelTest(TestCase):

    def setUp(self):

        self.encarregado_user = User.objects.create_user(
            email="joao@exemplo.com",
            nome="João Silva",
            role=User.Cargo.ENCARREGADO,
            password="senha123"
        )
        self.encarregado = Encarregado.objects.create(
            user=self.encarregado_user,
            telefone="+258821234500",
            endereco="Rua Teste, 123",
            nrBI="123456789012A"
        )

    def test_criar_aluno_sucesso(self):
        aluno_user = User.objects.create_user(
            email="aluno@exemplo.com",
            nome="Maria Oliveira",
            role=User.Cargo.ALUNO,
            password="senha123"
        )
        aluno = Aluno.objects.create(
            user=aluno_user,
            encarregado=self.encarregado,
            data_nascimento=date(2010, 5, 15),
            nrBI="123456789012B",
            escola_dest="Escola Primária",
            classe="5º Ano",
            mensalidade=Decimal("1500.00")
        )
        self.assertEqual(aluno.idade, 15)
        self.assertEqual(aluno.user.role, User.Cargo.ALUNO)
        self.assertEqual(str(aluno), f"Aluno: {aluno_user.nome} - {aluno_user.email}")

    def test_criar_aluno_muito_jovem(self):
        aluno_user = User.objects.create_user(
            email="aluno_muito_jovem@exemplo.com",
            nome="Pedro Souza",
            role=User.Cargo.ALUNO,
            password="senha123"
        )
        aluno = Aluno(
            user=aluno_user,
            encarregado=self.encarregado,
            data_nascimento=date.today() - timedelta(days = 365 * 3),  # 2 anos de idade
            nrBI="123456789012C",
            escola_dest="Creche",
            classe="Pre-Escolar",
            mensalidade=Decimal("1400.00")
        )
        with self.assertRaises(ValidationError) as context:
            aluno.full_clean()
        self.assertIn("O aluno deve ter pelo menos 3 anos de idade.", str(context.exception))

class MotoristaModelTest(TestCase):

    def test_criar_motorista_sucesso(self):
        motorista_user = User.objects.create_user(
            email="motorista@exemplo.com",
            nome="Carlos Pereira",
            role=User.Cargo.MOTORISTA,
            password="senha123"
        )
        motorista = Motorista.objects.create(
            user=motorista_user,
            data_nascimento=date.today() - timedelta(days = 365 * 30),  # 30 anos de idade
            nrBI="123456789012D",
            carta_conducao="985764187",
            validade_da_carta=date.today() + timedelta(days = 365 * 5),
            telefone="+258821234500",
            endereco="Rua Teste, 123"
        )
        self.assertEqual(motorista.user.role, User.Cargo.MOTORISTA)
        self.assertEqual(str(motorista), f"Motorista: {motorista_user.nome} - {motorista_user.email}")

    def test_motorista_muito_jovem(self):
        motorista_user = User.objects.create_user(
            email="motorista_muito_jovem@exemplo.com",
            nome="Ana Costa",
            role=User.Cargo.MOTORISTA,
            password="senha123"
        )
        motorista = Motorista(
            user=motorista_user,
            data_nascimento = date.today() - timedelta(days = 365 * 15),  # 15 anos de idade
            nrBI="123456789012E",
            carta_conducao="748769769",
            validade_da_carta=date.today() + timedelta(days = 365 * 5),
            telefone="+258821234500",
            endereco="Rua Teste, 123"
        )
        with self.assertRaises(ValidationError) as context:
            motorista.full_clean()
        self.assertIn("O motorista deve ter pelo menos 18 anos.", str(context.exception))

    def test_motorista_carta_expirada(self):
        motorista_user = User.objects.create_user(
            email="motorista_expirada@exemplo.com",
            nome="Bruno Lima",
            role=User.Cargo.MOTORISTA,
            password="senha123"
        )
        motorista = Motorista(
            user = motorista_user,
            data_nascimento = date.today() - timedelta(days = 365 * 30),
            nrBI = "123456789012F",
            carta_conducao = "125478912",
            validade_da_carta = date.today() - timedelta(days=30),
            telefone="+258821234500",
            endereco="Rua Teste, 123"
        )
        with self.assertRaises(ValidationError) as context:
            motorista.full_clean()
        self.assertIn("A carta de condução está expirada.", str(context.exception))

    def test_motorista_salario_negativo(self):
        motorista_user = User.objects.create_user(
            email="motorista_salario@exemplo.com",
            nome="Carlos Mendonsa",
            role=User.Cargo.MOTORISTA,
            password="senha123"
        )
        motorista = Motorista(
            user=motorista_user,
            data_nascimento=date.today() - timedelta(days = 365 * 30),
            nrBI="123456789012G",
            carta_conducao="987654321",
            validade_da_carta=date.today() + timedelta(days = 365 * 5),
            telefone="+258821234500",
            endereco="Rua Teste, 123",
            salario=Decimal("-12000.00")
        )
        with self.assertRaises(ValidationError) as context:
            motorista.full_clean()
        self.assertIn("O salario nao pode ser negativo.", str(context.exception))
