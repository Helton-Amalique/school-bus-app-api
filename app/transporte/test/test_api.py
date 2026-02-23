from django.test import TestCase
from django.urls import reverse
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from core.models import Aluno, Motorista, Encarregado
from transporte.models import Veiculo, Rota

User = get_user_model()

ROTAS_URL = reverse('transportes:rota-list')
VEICULOS_URL =reverse('transportes:veiculo-list')


class TransportesErrorAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Admin
        self.admin = User.objects.create_superuser(email='admin@test.com', password='pass1223', nome='Admin')

        # Motorista
        self.u_mot = User.objects.create_user(email='mot@test.com', password='passtest', nome='M', role='MOTORISTA')
        self.motorista = Motorista.objects.create(user=self.u_mot, data_nascimento='1990-01-01', nrBI='123456789012M', carta_conducao=123956789, validade_da_carta=date.today() + timedelta(days=365))
        self.veiculo_mot = Veiculo.objects.create(marca='Toyota', modelo='Hiace', matricula='ABC-1234', capacidade=15, motorista=self.motorista)
        self.rota_mot = Rota.objects.create(nome='Rota do Motorista', veiculo=self.veiculo_mot)

        # Outro motorista e rota
        self.u_mot2 = User.objects.create_user(email='mot2@test.com', password='passtest', nome='M2', role='MOTORISTA')
        self.motorista2 = Motorista.objects.create(user=self.u_mot2, data_nascimento='1992-01-01', nrBI='987654321098M', carta_conducao=129176789, validade_da_carta=date.today() + timedelta(days=365))
        self.veiculo_mot2 = Veiculo.objects.create(marca='Ford', modelo='Transit', matricula='XYZ-999-MP', capacidade=10, motorista=self.motorista2)
        self.rota_mot2 = Rota.objects.create(nome='Rota Alheia', veiculo=self.veiculo_mot2)

        # Encarregado e aluno
        self.u_enc = User.objects.create_user(email='enc@test.com', password='pass1236', nome='Elena', role='ENCARREGADO')
        self.encarregado = Encarregado.objects.create(user=self.u_enc)
        self.u_aluno = User.objects.create_user(email='aluno@test.com', password='pass7845', nome='Andre', role='ALUNO')
        self.aluno = Aluno.objects.create(user=self.u_aluno, encarregado=self.encarregado, data_nascimento='2005-01-01', nrBI='123456789012A')

    def test_aluno_nao_acede_rotas(self):
        """Aluno não deve conseguir listar rotas"""
        self.client.force_authenticate(user=self.u_aluno)
        res = self.client.get(ROTAS_URL)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_encarregado_nao_cria_rota(self):
        """Encarregado não deve conseguir criar rotas"""
        self.client.force_authenticate(user=self.u_enc)
        payload = {'nome': 'Rota Teste', 'veiculo': self.veiculo_mot.id}
        res = self.client.post(ROTAS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_motorista_nao_ve_rota_de_outro(self):
        """Motorista não deve conseguir ver rota de outro motorista"""
        self.client.force_authenticate(user=self.u_mot)
        url = reverse('transportes:rota-detail', args=[self.rota_mot2.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_motorista_nao_cria_rota(self):
        """Motorista não deve conseguir criar rotas"""
        self.client.force_authenticate(user=self.u_mot)
        payload = {'nome': 'Nova Rota', 'veiculo': self.veiculo_mot.id}
        res = self.client.post(ROTAS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_vagas_disponiveis_sem_rota(self):
        """Endpoint deve retornar vagas = capacidade total quando não há rota ativa"""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(VEICULOS_URL)

        data = next(item for item in res.data if item["id"] == self.veiculo_mot.id)
        self.assertEqual(data["vagas_disponiveis"], 15)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # self.assertEqual(res.data[0]["vagas_disponiveis"], 20)

    def test_vagas_disponiveis_com_alunos(self):
        """Endpoint deve retornar vagas corretas quando há rota com alunos"""
        veiculo = self.veiculo_mot
        rota = Rota.objects.create(nome="Rota Teste", veiculo=veiculo)

        al1 =User.objects.create_user(email="alq@test.com", password="pass1234", nome="Alq", role="ALUNO")
        aluno1 = Aluno.objects.create(user=al1, encarregado=self.encarregado, data_nascimento='2005-01-19', nrBI='123456789012B')
        al2 =User.objects.create_user(email="al2@test.com", password="pass1234", nome="Al2", role="ALUNO")
        aluno2 = Aluno.objects.create(user=al2, encarregado=self.encarregado, data_nascimento='2005-10-01', nrBI='123456789012C')
        rota.alunos.add(aluno1, aluno2)

        self.client.force_authenticate(user=self.admin)
        res = self.client.get(VEICULOS_URL)
        data = next(item for item in res.data if item["id"] == self.veiculo_mot.id)
        self.assertEqual(data["vagas_disponiveis"], 13)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_vagas_disponiveis_nao_negativas(self):
        """Endpoint deve garantir que vagas_disponiveis nunca seja negativo, mesmo com mais alunos que capacidade"""
        v_plotado = Veiculo.objects.create(marca="Mercedes", modelo="Sprinter", matricula="LOT-123-TT", capacidade=2, motorista=self.motorista)
        rota = Rota.objects.create(nome="Rota Lotada", veiculo=v_plotado)
        for i in range(4):
            u = User.objects.create_user(email=f"aluno{i}@test.com", password="passtest", role="ALUNO", nome=f"Aluno{i}")
            aluno = Aluno.objects.create(user=u, encarregado=self.encarregado, data_nascimento='2005-01-01', nrBI=f'123456789012{i}A')
            rota.alunos.add(aluno)

        self.client.force_authenticate(user=self.admin)
        res = self.client.get(VEICULOS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        veiculo_data = next(v for v in res.data if v["id"] == v_plotado.id)
        self.assertEqual(veiculo_data["vagas_disponiveis"], 0)
