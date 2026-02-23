# import datetime
# from datetime import date, timedelta
# from django.test import TestCase
# from core.models import Motorista, Aluno, Encarregado
# from transporte.models import Veiculo, Rota
# from django.contrib.auth import get_user_model
# from django.core.exceptions import ValidationError

# User = get_user_model()

# class TransportModelTest(TestCase):

#     def setUp(self):
#         self.user_mot = User.objects.create_user(
#             email="mot@test.com", password="transppass", nome="Motorista", role="MOTORISTA"
#         )
#         self.motorista = Motorista.objects.create(
#             user=self.user_mot, data_nascimento="1990-04-25", nrBI="547849761897P",
#             carta_conducao="987451237", validade_da_carta=date.today() + timedelta(days=365)
#         )
#         self.veiculo = Veiculo.objects.create(
#             marca="Toyota", modelo="Hiace",
#             matricula="AOC-785-MP",
#             capacidade=25,
#             motorista=self.motorista
#         )
#         self.u_enc = User.objects.create_user(email="enc@test.com", password="passtest", role="ENCARREGADO", nome='Encarrgedo Teste')
#         self.encarregado = Encarregado.objects.create(user=self.u_enc, nrBI="123456789012E")


#     def _criar_aluno(self, email, bi):
#         """Método auxiliar para criar alunos com todos os campos obrigatórios"""
#         user = User.objects.create_user(
#         email=email,
#         password="password123",
#         role="ALUNO",
#         nome="Aluno Teste" # <--- O argumento que faltava
#         )
#         return Aluno.objects.create(
#         user=user,
#         encarregado=self.encarregado, # Usando o do setUp
#         nrBI=bi,
#         data_nascimento="2015-01-01"
#         )

#     def test_vagas_disponiveis(self):
#         """verifica se o calc d vagas responde ao numero de alunos"""
#         # rota = Rota.objects.create(nome="Rota Norte", veiculo=self.veiculo)
#         self.assertEqual(self.veiculo.vagas_disponiveis, 25)

#     def test_chegada_invalida(self):
#         """Erre se a chagada for antes da partida"""
#         rota = Rota(nome="Rota Errada", veiculo=self.veiculo, hora_partida=datetime.time(12, 0), hora_chegada=datetime.time(10, 0))
#         with self.assertRaises(ValidationError):
#             rota.full_clean()

#     def test_matricula_normalizada(self):
#         """Garante de a matricula fica sempre em uppercase"""
#         veiculo = Veiculo.objects.create(
#             marca = "Nissan", modelo = "Caravan",
#             matricula = "acb-111-mp", capacidade=25
#         )
#         self.assertEqual(veiculo.matricula, "ACB-111-MP")

#     def test_erro_sem_motorista(self):
#         veiculo_sem= Veiculo.objects.create(marca="Ford", modelo="Transit", matricula="APO-009-MC", capacidade=12)
#         rota= Rota(nome="Rota Fantasma", veiculo=veiculo_sem)

#         with self.assertRaises(ValidationError):
#             rota.full_clean()

#     def test_rota_excede_capacidade(self):
#         """Erro se o numero de alunos exceder a capacidade do veiculo"""
#         aluno1 = Aluno.objects.create(user=User.objects.create_user(email="a1@test.com", password="passtest", role="ALUNO"))
#         aluno2 = Aluno.objects.create(user=User.objects.create_user(email="a2@test.com", password="passtest", role="ALUNO"))
#         aluno3 = Aluno.objects.create(user=User.objects.create_user(email="a3@test.com", password="passtest", role="ALUNO"))

#         rota = Rota(
#             nome="Rota Correta",
#             veiculo=self.veiculo,
#             hora_partida=datetime.time(6, 0),
#             hora_chegada=datetime.time(7, 0)
#         )
#         rota.save()
#         rota.alunos.add(aluno1, aluno2, aluno3)

#         with self.assertRaises(ValidationError):
#             rota.full_clean()

#     def test_rota_nao_excede(self):
#         aluno1 = Aluno.objects.create(user=User.objects.create_user(email="a1@test.com", password="passtest", nome="sheila", role="ALUNO"))
#         aluno2 = Aluno.objects.create(user=User.objects.create_user(email="a2@test.com", password="passtest", role="ALUNO"))
#         rota = Rota(
#             nome="Rota Correta",
#             veiculo=self.veiculo,
#             hora_partida=datetime.time(6, 0),
#             hora_chegada=datetime.time(7, 0)
#         )
#         rota.save()
#         rota.alunos.add(aluno1, aluno2)

#         rota.full_clean()

#     def test_sem_vagas(self):
#         """Se não houver rota ativa, vagas = capacidade total"""
#         self.assertEqual(self.veiculo.vagas_disponiveis, 25)

#     def test_vagas_com_rota_sem_alunos(self):
#         """Rota ativa sem alunos → vagas = capacidade total"""
#         rota = Rota.objects.create(nome="Rota Norte", veiculo=self.veiculo)
#         self.assertEqual(self.veiculo.vagas_disponiveis, 25)

#     # def test_vagas_com_alunos(self):
#     #     """Rota ativa com alunos → vagas = capacidade - alunos"""
#     #     rota = Rota.objects.create(nome="Rota Sul", veiculo=self.veiculo)
#     #     aluno1 = Aluno.objects.create(user=User.objects.create_user(email="a1@test.com", password="passtest", role="ALUNO"))
#     #     aluno2 = Aluno.objects.create(user=User.objects.create_user(email="a2@test.com", password="passtest", role="ALUNO"))
#     #     rota.alunos.add(aluno1, aluno2)

#     #     self.assertEqual(self.veiculo.vagas_disponiveis, 1)

#     # def test_vagas_nao_ficam_negativas(self):
#     #     """Mesmo com excesso de alunos, vagas nunca ficam negativas"""
#     #     rota = Rota.objects.create(nome="Rota Lotada", veiculo=self.veiculo)
#     #     aluno1 = Aluno.objects.create(user=User.objects.create_user(email="a3@test.com", password="passtest1", role="ALUNO"))
#     #     aluno2 = Aluno.objects.create(user=User.objects.create_user(email="a4@test.com", password="passtest2", role="ALUNO"))
#     #     aluno3 = Aluno.objects.create(user=User.objects.create_user(email="a5@test.com", password="passtest3", role="ALUNO"))
#     #     aluno4 = Aluno.objects.create(user=User.objects.create_user(email="a6@test.com", password="passtest4", role="ALUNO"))

#     #     rota.alunos.add(aluno1, aluno2, aluno3, aluno4)

#     #     self.assertEqual(self.veiculo.vagas_disponiveis, 0)

#     def test_rota_sem_veiculo(self):
#         """Erro se rota for criada sem veículo"""
#         rota = Rota(nome="Rota Fantasma")
#         with self.assertRaises(ValidationError):
#             rota.full_clean()

#     def test_motorista_carta_expirada(self):
#         """Erro se motorista tiver carta expirada"""
#         user_exp = User.objects.create_user(email="exp@test.com", password="passtest", role="MOTORISTA")
#         motorista_exp = Motorista(
#         user=user_exp, data_nascimento="1985-01-01", nrBI="111111111111E",
#         carta_conducao="999999999", validade_da_carta=date.today() - timedelta(days=1))

#         with self.assertRaises(ValidationError):
#             motorista_exp.full_clean()
