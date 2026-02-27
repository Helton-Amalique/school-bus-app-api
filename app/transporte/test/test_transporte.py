import datetime
from datetime import date, timedelta
from django.test import TestCase
from core.models import Motorista, Aluno, Encarregado
from transporte.models import Veiculo, Rota, Manutencao
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class TransportTestCase(TestCase):

    def setUp(self):
        self.user_mot = User.objects.create_user(
            email="mot@test.com", password="transppass", nome="Motorista", role="MOTORISTA"
        )
        self.motorista = Motorista.objects.create(
            user=self.user_mot, data_nascimento="1990-04-25", nrBI="547849761897P",
            carta_conducao="987451237", validade_da_carta=date.today() + timedelta(days=365)
        )
        self.veiculo = Veiculo.objects.create(
            marca="Toyota", modelo="Hiace",
            matricula="AOC-785-MP",
            capacidade=25,
            motorista=self.motorista
        )
        self.u_enc = User.objects.create_user(email="enc@test.com", password="passtest", role="ENCARREGADO", nome='Encarrgedo Teste')
        self.encarregado = Encarregado.objects.create(user=self.u_enc, nrBI="123456789012E")


# ******* TESTES DE VEÍCULO ******
#
    def _criar_motorista_unico(self, sufixo):
        """Cria um utilizador e motorista com dados únicos para evitar conflitos."""
        user = User.objects.create_user(
            email=f"motorista_{sufixo}@test.com",
            password="password123",
            nome=f"Motorista {sufixo}",
            role="MOTORISTA"
        )
        return Motorista.objects.create(
            user=user,
            data_nascimento="1990-01-01",
            nrBI=f"{sufixo:0>12}X",
            carta_conducao=f"987654{sufixo:0>3}",
            validade_da_carta=date.today() + timedelta(days=365)
        )

    def test_veiculo_capacidade_positiva(self):
        novo_motorista = self._criar_motorista_unico(sufixo="2")
        veiculo = Veiculo(
            marca="Toyota",
            modelo="Hiace",
            matricula="MMW-123-MC",
            capacidade=15,
            motorista=novo_motorista
        )

        veiculo.full_clean()
        self.assertEqual(veiculo.capacidade, 15)

    def test_dois_veiculos_ativos_nao_podem_ter_mesmo_motorista(self):
        veiculo2 = Veiculo(
            marca="Ford",
            modelo="Transit",
            matricula="ABC-789-MC",
            capacidade=10,
            motorista=self.motorista
        )
        with self.assertRaises(ValidationError):
            veiculo2.full_clean()

    def test_veiculo_com_motorista(self):
        motorista_test = self._criar_motorista_unico(sufixo="3")
        veiculo = Veiculo(marca="Toyota", modelo="Quantum", matricula="XYZ-456-MC", capacidade=30, motorista=motorista_test)
        try:
            veiculo.full_clean()
        except ValidationError:
            self.fail("Veículo com motorista válido não deve lançar ValidationError")

    def test_veiculo_sem_motorista(self):
        veiculo = Veiculo(marca="Toyota", modelo="Hiace", matricula="AEC-785-MP", capacidade=25, motorista=None)
        with self.assertRaises(ValidationError) as err:
            veiculo.full_clean()
        self.assertIn("motorista", err.exception.message_dict)
        self.assertEqual(err.exception.message_dict["motorista"], ["O veículo deve ter um motorista atribuído."])

    def test_veiculo_inativo(self):
        m_inativo=self._criar_motorista_unico(sufixo=33)
        veiculo = Veiculo(marca="Toyota", modelo="Hiace", matricula="AHC-785-MP", capacidade=25, motorista=m_inativo, ativo=False)
        try:
            veiculo.full_clean()
        except ValidationError:
            self.fail("Veículo inativo não deve lançar ValidationError")

    # def test_veiculo_capacidade_minima(self):
    #     veiculo = Veiculo(marca="Toyota", modelo="Hiace", matricula="ACC-785-MP", capacidade=1, motorista=self.motorista)
    #     try:
    #         veiculo.full_clean()
    #     except ValidationError:
    #         self.fail("Veículo com capacidade mínima válida não deve lançar ValidationError")

    def test_veiculo_em_manutencao(self):
        m_mant = self._criar_motorista_unico(sufixo="88")
        veiculo = Veiculo.objects.create(marca="Toyota", modelo="Hiace", matricula="AZC-785-MP", capacidade=25, motorista=m_mant)

        Manutencao.objects.create(
            veiculo=veiculo,
            descricao="Reparação",
            data_inicio=date.today(),
            concluida=False
        )
        try:
            veiculo.full_clean()
        except ValidationError as er:
            self.fail(f"Veículo em manutenção não deve lançar ValidationError. Erro: {er}")

    def test_veiculo_capacidade_excessiva(self):
        m_novo = self._criar_motorista_unico(sufixo="4")
        veiculo = Veiculo(marca="Toyota", modelo="Hiace", matricula="AQC-785-MP", capacidade=51, motorista=m_novo)
        with self.assertRaises(ValidationError) as err:
            veiculo.full_clean()
        self.assertIn("capacidade", err.exception.message_dict)
        self.assertEqual(err.exception.message_dict["capacidade"], ["A capacidade do veículo deve ser menor ou igual a 50."])

    def test_dois_veiculos_mesma_matricula(self):
        matricula_rep = "AMC-785-MP"
        matr1 = self._criar_motorista_unico(sufixo="5")
        matr2 = self._criar_motorista_unico(sufixo="6")
        Veiculo.objects.create(marca="Toyota", modelo="Hiace", matricula=matricula_rep, capacidade=25, motorista=matr1)
        veiculo2 = Veiculo(marca="Toyota", modelo="Hiace", matricula=matricula_rep, capacidade=25, motorista=matr2)
        with self.assertRaises(ValidationError) as err:
            veiculo2.full_clean()
        self.assertIn("matricula", err.exception.message_dict)
        self.assertEqual(err.exception.message_dict["matricula"], ["A matrícula do veículo já está em uso."])

# # ******* TESTES DE VAGAS ******
    def test_vagas_disponiveis(self):
        rota = Rota.objects.create(nome="Rota Teste", veiculo=self.veiculo, hora_partida=datetime.time(7, 0), hora_chegada=datetime.time(8, 0))
        for i in range(1):
            letra = chr(65 + (i % 26))
            bi_valido = f'{str(i).zfill(12)}{letra}'
            u_aluno = User.objects.create_user(email=f"aluno{i}@test.com", password="passtest", role="ALUNO", nome=f'Aluno Teste {i}')
            aluno = Aluno.objects.create(user=u_aluno, encarregado=self.encarregado, data_nascimento=date(2005, 5, 15), nrBI=bi_valido, escola_dest="Escola Basica do Guava", classe="1", mensalidade=2500.00)
            rota.alunos.add(aluno)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.vagas_disponiveis, 24)

    def test_vagas_disponiveis_zero(self):
        rota = Rota.objects.create(nome="Rota Lotacao Maxima", veiculo=self.veiculo, hora_partida=datetime.time(7, 0), hora_chegada=datetime.time(8, 0))
        for i in range(25):
            letra = chr(65 + (i % 26))
            bi_valido = f'{str(i).zfill(12)}{letra}'
            u_aluno = User.objects.create_user(email=f"aluno{i}@test.com", password="passtest", role="ALUNO", nome=f'Aluno Teste {i}')
            aluno = Aluno.objects.create(user=u_aluno, encarregado=self.encarregado, data_nascimento=date(2005, 5, 15), nrBI=bi_valido, escola_dest="Escola Basica do Guava", classe="1", mensalidade=2500.00)
            rota.alunos.add(aluno)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.vagas_disponiveis, 0)

    def test_vagas_sem_alunos(self):
        rota = Rota.objects.create(nome="Rota Teste", veiculo=self.veiculo, ativo=True, hora_partida=datetime.time(7, 0), hora_chegada=datetime.time(8, 0))
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.vagas_disponiveis, 25)

    def test_vagas_quase_cheias(self):
        rota = Rota.objects.create(nome="Rota Teste", veiculo=self.veiculo, hora_partida=datetime.time(7, 0), hora_chegada=datetime.time(8, 0))
        for i in range(24):
            letra = chr(65 + (i % 26))
            bi_valido = f'{str(i).zfill(12)}{letra}'  # Garante que o BI tem 12 dígitos seguidos de uma letra
            u_aluno = User.objects.create_user(email=f"aluno{i}@test.com", password="passtest", role="ALUNO", nome=f'Aluno Teste {i}')
            aluno = Aluno.objects.create(user=u_aluno, encarregado=self.encarregado, data_nascimento=date(2005, 5, 15), nrBI=bi_valido, escola_dest="Escola Basica do Guava", classe="1", mensalidade=2500.00)
            rota.alunos.add(aluno)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.vagas_disponiveis, 1)

# ******* TESTES DE ROTA ******

    def test_rota_sem_motorista(self):
        Veiculo.objects.filter(pk=self.veiculo.pk).update(motorista=None)
        self.veiculo.refresh_from_db()
        rota = Rota(nome="Rota Teste", veiculo=self.veiculo)
        with self.assertRaises(ValidationError):
            rota.full_clean()

    def test_confito_rota_ativa(self):
        Rota.objects.create(nome="Rota Ativa", veiculo=self.veiculo, ativo=True)
        rota2 = Rota(nome="Rota Ativa 2", veiculo=self.veiculo, ativo=True)
        with self.assertRaises(ValidationError):
            rota2.full_clean()

    def test_rota_inativa(self):
        Rota.objects.create(nome="Rota Inativa", veiculo=self.veiculo, ativo=False)
        rota2 = Rota(nome="Rota Inativa 2", veiculo=self.veiculo, ativo=False)
        try:
            rota2.full_clean()
        except ValidationError:
            self.fail("Rota inativa não deve lançar ValidationError")

    def test_rota_sem_veiculo(self):
        rota = Rota(nome="Rota Teste", hora_partida=datetime.time(7, 0), hora_chegada=datetime.time(8, 0))
        with self.assertRaises(ValidationError) as er:
            rota.full_clean()
        self.assertIn("veiculo", er.exception.message_dict)

    def test_inpedir_rota_com_veiculo_em_manutencao(self):
        m2 = self._criar_motorista_unico(sufixo="99")
        v2 = Veiculo.objects.create(
            marca="Toyota", modelo="Hiace",
            matricula="AMC-785-MP", capacidade=25, motorista=m2
        )

        Manutencao.objects.create(
            veiculo=v2,
            descricao="Reparação",
            data_inicio=date.today(),
            concluida=False
        )
        rota = Rota(nome="Rota Oficina", veiculo=v2)
        with self.assertRaises(ValidationError):
            rota.full_clean()
