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
