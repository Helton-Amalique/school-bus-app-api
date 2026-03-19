"""
tests/transporte/test_transporte.py
====================================
Testes de modelos, signals e API do módulo transporte.

Executar:
    python manage.py test tests.transporte
    python manage.py test tests.transporte.test_transporte.VeiculoModelTests
"""

import datetime
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from rest_framework import status

from tests.base import BaseAPITestCase, BaseTestCase
from tests.factories import (
    criar_aluno,
    criar_manutencao,
    criar_motorista,
    criar_rota,
    criar_transporte_aluno,
    criar_user,
    criar_veiculo,
    data_futura,
    data_passada,
)


# ══════════════════════════════════════════════
# VEICULO MANAGER
# ══════════════════════════════════════════════

class VeiculoManagerTests(TestCase):

    def test_ativos_exclui_inativos(self):
        from transporte.models import Veiculo
        v_ativo = criar_veiculo()
        v_inativo = criar_veiculo()
        Veiculo.objects.filter(pk=v_inativo.pk).update(ativo=False)

        ativos = list(Veiculo.objects.ativos())
        self.assertIn(v_ativo, ativos)
        self.assertNotIn(v_inativo, ativos)

    def test_com_vagas_exclui_veiculo_cheio(self):
        from transporte.models import Veiculo
        v = criar_veiculo(capacidade=1)
        rota = criar_rota(veiculo=v)
        rota.alunos.add(criar_aluno())

        pks = list(Veiculo.objects.com_vagas().values_list('pk', flat=True))
        self.assertNotIn(v.pk, pks)

    def test_com_vagas_inclui_veiculo_com_espaco(self):
        from transporte.models import Veiculo
        v = criar_veiculo(capacidade=10)
        criar_rota(veiculo=v)

        pks = list(Veiculo.objects.com_vagas().values_list('pk', flat=True))
        self.assertIn(v.pk, pks)


# ══════════════════════════════════════════════
# VEICULO — MODELO
# ══════════════════════════════════════════════

class VeiculoModelTests(TestCase):

    def test_criar_veiculo_valido(self):
        self.assertIsNotNone(criar_veiculo().pk)

    def test_matricula_formato_invalido_levanta_erro(self):
        from transporte.models import Veiculo
        m = criar_motorista()
        v = Veiculo(
            marca='Toyota', modelo='Hiace', matricula='INVALIDA',
            capacidade=10, motorista=m,
            data_validade_seguro=data_futura(365),
            data_validade_inspecao=data_futura(365),
            data_validade_manifesto=data_futura(365),
        )
        with self.assertRaises(ValidationError):
            v.full_clean()

    def test_sem_motorista_levanta_erro(self):
        from transporte.models import Veiculo
        v = Veiculo(
            marca='Toyota', modelo='Hiace', matricula='BBB-001-XY',
            capacidade=10, motorista=None,
            data_validade_seguro=data_futura(365),
            data_validade_inspecao=data_futura(365),
            data_validade_manifesto=data_futura(365),
        )
        with self.assertRaises(ValidationError):
            v.full_clean()

    def test_vagas_disponiveis_sem_rota(self):
        v = criar_veiculo(capacidade=15)
        self.assertEqual(v.vagas_disponiveis, 15)

    def test_vagas_disponiveis_com_alunos(self):
        v = criar_veiculo(capacidade=10)
        rota = criar_rota(veiculo=v)
        for _ in range(3):
            rota.alunos.add(criar_aluno())
        self.assertEqual(v.vagas_disponiveis, 7)

    def test_em_manutencao_true_com_manutencao_aberta(self):
        v = criar_veiculo()
        criar_manutencao(veiculo=v, concluida=False)
        self.assertTrue(v.em_manutencao())

    def test_em_manutencao_false_apos_concluir(self):
        v = criar_veiculo()
        m = criar_manutencao(veiculo=v, concluida=False)
        m.concluida = True
        m.save()
        self.assertFalse(v.em_manutencao())

    def test_document_em_dia_com_docs_validos(self):
        self.assertTrue(criar_veiculo().document_em_dia())

    def test_document_em_dia_false_com_seguro_vencido(self):
        from transporte.models import Veiculo
        v = criar_veiculo()
        Veiculo.objects.filter(pk=v.pk).update(data_validade_seguro=data_passada(10))
        v.refresh_from_db()
        self.assertFalse(v.document_em_dia())

    def test_consumo_medio_sem_abastecimentos_retorna_zero(self):
        self.assertEqual(criar_veiculo().consumo_medio(), 0.0)

    def test_str_contem_matricula(self):
        v = criar_veiculo()
        self.assertIn(v.matricula, str(v))


# ══════════════════════════════════════════════
# ROTA — MODELO
# ══════════════════════════════════════════════

class RotaModelTests(TestCase):

    def test_criar_rota_valida(self):
        self.assertIsNotNone(criar_rota().pk)

    def test_hora_chegada_antes_partida_levanta_erro(self):
        from transporte.models import Rota
        v = criar_veiculo()
        rota = Rota(
            nome='Rota Inválida', veiculo=v,
            hora_partida=datetime.time(8, 0),
            hora_chegada=datetime.time(7, 0),
        )
        with self.assertRaises(ValidationError):
            rota.clean()

    def test_total_inscritos(self):
        rota = criar_rota()
        for _ in range(4):
            rota.alunos.add(criar_aluno())
        self.assertEqual(rota.total_inscritos, 4)

    def test_motorista_atalho(self):
        motorista = criar_motorista()
        rota = criar_rota(veiculo=criar_veiculo(motorista=motorista))
        self.assertEqual(rota.motorista, motorista)

    def test_conflito_horario_mesmo_veiculo_levanta_erro(self):
        from transporte.models import Rota
        v = criar_veiculo()
        criar_rota(
            veiculo=v, nome='Rota A',
            hora_partida=datetime.time(6, 0),
            hora_chegada=datetime.time(8, 0),
        )
        rota2 = Rota(
            nome='Rota B', veiculo=v,
            hora_partida=datetime.time(7, 0),
            hora_chegada=datetime.time(9, 0),
        )
        with self.assertRaises(ValidationError):
            rota2.clean()

    def test_str_contem_rota(self):
        self.assertIn('Rota', str(criar_rota()))


# ══════════════════════════════════════════════
# TRANSPORTE ALUNO
# ══════════════════════════════════════════════

class TransporteAlunoTests(TestCase):

    def test_criar_registo_valido(self):
        aluno = criar_aluno()
        rota = criar_rota()
        rota.alunos.add(aluno)
        t = criar_transporte_aluno(aluno=aluno, rota=rota)
        self.assertIsNotNone(t.pk)

    def test_constraint_unica_por_aluno_rota_dia(self):
        from django.db import IntegrityError
        from transporte.models import TransporteAluno
        aluno = criar_aluno()
        rota = criar_rota()
        rota.alunos.add(aluno)
        hoje = datetime.date.today()
        TransporteAluno.objects.create(aluno=aluno, rota=rota, data=hoje, status='PENDENTE')
        with self.assertRaises(IntegrityError):
            TransporteAluno.objects.create(aluno=aluno, rota=rota, data=hoje, status='EMBARCADO')

    def test_aluno_nao_inscrito_levanta_erro(self):
        from transporte.models import TransporteAluno
        aluno = criar_aluno()
        rota = criar_rota()  # aluno não está inscrito
        t = TransporteAluno(aluno=aluno, rota=rota, status='PENDENTE')
        with self.assertRaises(ValidationError):
            t.clean()

    def test_str_contem_status(self):
        self.assertIn('PENDENTE', str(criar_transporte_aluno()))


# ══════════════════════════════════════════════
# MANUTENCAO
# ══════════════════════════════════════════════

class ManutencaoTests(TestCase):

    def test_criar_manutencao_valida(self):
        self.assertIsNotNone(criar_manutencao().pk)

    def test_data_fim_antes_inicio_levanta_erro(self):
        from transporte.models import Manutencao
        v = criar_veiculo()
        m = Manutencao(
            veiculo=v, tipo='PREVENTIVA', descricao='Revisão',
            data_inicio=datetime.date.today(),
            data_fim=data_passada(5),
            quilometragem_no_momento_revisao=0,
        )
        with self.assertRaises(ValidationError):
            m.clean()

    def test_concluir_manutencao_actualiza_veiculo(self):
        v = criar_veiculo()
        m = criar_manutencao(veiculo=v, concluida=False)
        m.concluir_manutencao(km_proximo_ajuste=5000)
        v.refresh_from_db()
        self.assertTrue(m.concluida)
        self.assertIsNotNone(v.data_ultima_revisao)

    def test_veiculo_sai_de_manutencao_apos_concluir(self):
        v = criar_veiculo()
        m = criar_manutencao(veiculo=v, concluida=False)
        self.assertTrue(v.em_manutencao())
        m.concluir_manutencao()
        self.assertFalse(v.em_manutencao())


# ══════════════════════════════════════════════
# ABASTECIMENTO
# ══════════════════════════════════════════════

class AbastecimentoTests(TestCase):

    def test_abastecimento_actualiza_quilometragem(self):
        from transporte.models import Abastecimento
        v = criar_veiculo()
        Abastecimento.objects.create(
            veiculo=v, data=datetime.date.today(),
            quilometragem_no_ato=500,
            quantidade_litros=Decimal('40.00'),
            custo_total=Decimal('2800.00'),
            posto_combustivel='Posto Central',
        )
        v.refresh_from_db()
        self.assertEqual(v.quilometragem_atual, 500)

    def test_quilometragem_menor_que_actual_levanta_erro(self):
        from transporte.models import Abastecimento, Veiculo
        v = criar_veiculo()
        Veiculo.objects.filter(pk=v.pk).update(quilometragem_atual=1000)
        v.refresh_from_db()
        a = Abastecimento(
            veiculo=v, quilometragem_no_ato=500,
            quantidade_litros=Decimal('40.00'),
            custo_total=Decimal('2800.00'),
            posto_combustivel='Posto X',
        )
        with self.assertRaises(ValidationError):
            a.clean()


# ══════════════════════════════════════════════
# SIGNALS — TRANSPORTE
# ══════════════════════════════════════════════

class SignalBloquearDeleteVeiculoTests(TestCase):

    def test_delete_veiculo_com_rota_levanta_permissao_negada(self):
        v = criar_veiculo()
        criar_rota(veiculo=v)
        with self.assertRaises(PermissionDenied):
            v.delete()

    def test_delete_veiculo_sem_rota_permitido(self):
        criar_veiculo().delete()  # não deve levantar excepção


class SignalDesactivarRotasManutencaoTests(TestCase):

    def test_iniciar_manutencao_desactiva_rotas_ativas(self):
        v = criar_veiculo()
        rota = criar_rota(veiculo=v, ativo=True)
        self.assertTrue(rota.ativo)
        criar_manutencao(veiculo=v)  # signal desactiva as rotas
        rota.refresh_from_db()
        self.assertFalse(rota.ativo)


# ══════════════════════════════════════════════
# API — VEICULOS
# ══════════════════════════════════════════════

class VeiculoAPITests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.autenticar_como_gestor(email='gestor_vei@teste.co.mz')
        self.veiculo = criar_veiculo()

    def test_listar_veiculos(self):
        resp = self.client.get('/api/v1/veiculos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_detalhe_veiculo(self):
        resp = self.client.get(f'/api/v1/veiculos/{self.veiculo.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['matricula'], self.veiculo.matricula)

    def test_criar_veiculo(self):
        motorista = criar_motorista()
        payload = {
            'marca': 'Mercedes', 'modelo': 'Sprinter',
            'matricula': 'MER-001-XY', 'capacidade': 20,
            'motorista': motorista.pk,
            'data_validade_seguro': data_futura(365).isoformat(),
            'data_validade_inspecao': data_futura(365).isoformat(),
            'data_validade_manifesto': data_futura(365).isoformat(),
            'nr_manifesto': 'MAN99999',
        }
        resp = self.client.post('/api/v1/veiculos/', payload)
        self.assertIn(resp.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])

    def test_sem_autenticacao_retorna_401(self):
        self.desautenticar()
        resp = self.client.get('/api/v1/veiculos/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ══════════════════════════════════════════════
# API — ROTAS
# ══════════════════════════════════════════════

class RotaAPITests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.autenticar_como_gestor(email='gestor_rot@teste.co.mz')
        self.rota = criar_rota()

    def test_listar_rotas(self):
        resp = self.client.get('/api/v1/rotas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_detalhe_rota(self):
        resp = self.client.get(f'/api/v1/rotas/{self.rota.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_filtrar_rotas_ativas(self):
        resp = self.client.get('/api/v1/rotas/', {'ativo': 'true'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ══════════════════════════════════════════════
# API — TRANSPORTE ALUNO
# ══════════════════════════════════════════════

class TransporteAlunoAPITests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.autenticar_como_gestor(email='gestor_ta@teste.co.mz')
        self.aluno = criar_aluno()
        self.rota = criar_rota()
        self.rota.alunos.add(self.aluno)
        self.transporte = criar_transporte_aluno(aluno=self.aluno, rota=self.rota)

    def test_listar_transportes(self):
        resp = self.client.get('/api/v1/transportes/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_check_in_action(self):
        resp = self.client.post(
            f'/api/v1/transportes/{self.transporte.pk}/check_in/',
            {'status': 'EMBARCADO'},
        )
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])


# ══════════════════════════════════════════════
# SIGNAL — ABASTECIMENTO → DESPESA VEICULO
# ══════════════════════════════════════════════

class SignalAbastecimentoDespesaVeiculoTests(TestCase):
    """
    Garante que ao criar um Abastecimento é criada automaticamente
    uma DespesaVeiculo do tipo COMBUSTIVEL no módulo financeiro.
    """

    def _criar_abastecimento(self, veiculo, litros='40.00', custo='2800.00', km=500):
        from transporte.models import Abastecimento
        return Abastecimento.objects.create(
            veiculo=veiculo,
            data=datetime.date.today(),
            quilometragem_no_ato=km,
            quantidade_litros=Decimal(litros),
            custo_total=Decimal(custo),
            posto_combustivel='Posto Central',
        )

    def test_abastecimento_cria_despesa_veiculo_combustivel(self):
        from financeiro.models import DespesaVeiculo
        v = criar_veiculo()
        self._criar_abastecimento(v)
        self.assertTrue(
            DespesaVeiculo.objects.filter(
                veiculo=v, tipo='COMBUSTIVEL'
            ).exists()
        )

    def test_valor_despesa_igual_ao_custo_do_abastecimento(self):
        from financeiro.models import DespesaVeiculo
        v = criar_veiculo()
        self._criar_abastecimento(v, custo='3500.00')
        despesa = DespesaVeiculo.objects.get(veiculo=v, tipo='COMBUSTIVEL')
        self.assertEqual(despesa.valor, Decimal('3500.00'))

    def test_despesa_tem_transacao_associada(self):
        from financeiro.models import DespesaVeiculo
        v = criar_veiculo()
        self._criar_abastecimento(v)
        despesa = DespesaVeiculo.objects.get(veiculo=v, tipo='COMBUSTIVEL')
        self.assertIsNotNone(despesa.transacao_id)

    def test_despesa_entra_no_balanco_mensal(self):
        from financeiro.models import BalancoMensal, DespesaVeiculo
        from tests.factories import criar_config_financeira
        criar_config_financeira()
        v = criar_veiculo()
        hoje = datetime.date.today()
        self._criar_abastecimento(v, custo='2800.00')

        balanco = BalancoMensal.gerar_balanco(hoje.month, hoje.year)
        self.assertGreater(balanco.total_despesas_frota, Decimal('0.00'))

    def test_dois_abastecimentos_criam_duas_despesas(self):
        from financeiro.models import DespesaVeiculo
        v = criar_veiculo()
        self._criar_abastecimento(v, km=500, custo='2800.00')
        self._criar_abastecimento(v, km=1000, custo='3100.00')
        qtd = DespesaVeiculo.objects.filter(veiculo=v, tipo='COMBUSTIVEL').count()
        self.assertEqual(qtd, 2)


# ══════════════════════════════════════════════
# SIGNAL — MANUTENÇÃO CONCLUÍDA → DESPESA VEICULO
# ══════════════════════════════════════════════

class SignalManutencaoDespesaVeiculoTests(TestCase):
    """
    Garante que ao concluir uma Manutenção com custo > 0 é criada
    automaticamente uma DespesaVeiculo do tipo MANUTENCAO.
    """

    def test_concluir_manutencao_cria_despesa_veiculo(self):
        from financeiro.models import DespesaVeiculo
        v = criar_veiculo()
        m = criar_manutencao(veiculo=v, concluida=False)
        m.concluir_manutencao()
        self.assertTrue(
            DespesaVeiculo.objects.filter(
                veiculo=v, tipo='MANUTENCAO'
            ).exists()
        )

    def test_valor_despesa_igual_ao_custo_da_manutencao(self):
        from financeiro.models import DespesaVeiculo
        from transporte.models import Manutencao
        v = criar_veiculo()
        m = criar_manutencao(veiculo=v, concluida=False)
        Manutencao.objects.filter(pk=m.pk).update(custo=Decimal('8500.00'))
        m.refresh_from_db()
        m.concluir_manutencao()
        despesa = DespesaVeiculo.objects.get(veiculo=v, tipo='MANUTENCAO')
        self.assertEqual(despesa.valor, Decimal('8500.00'))

    def test_manutencao_sem_custo_nao_cria_despesa(self):
        from financeiro.models import DespesaVeiculo
        from transporte.models import Manutencao
        v = criar_veiculo()
        m = criar_manutencao(veiculo=v, concluida=False)
        Manutencao.objects.filter(pk=m.pk).update(custo=Decimal('0.00'))
        m.refresh_from_db()
        m.concluir_manutencao()
        self.assertFalse(
            DespesaVeiculo.objects.filter(veiculo=v, tipo='MANUTENCAO').exists()
        )

    def test_concluir_duas_vezes_nao_duplica_despesa(self):
        """Idempotência — mesma data + veículo + tipo + valor não duplica."""
        from financeiro.models import DespesaVeiculo
        from transporte.models import Manutencao
        v = criar_veiculo()
        m = criar_manutencao(veiculo=v, concluida=False)
        m.concluir_manutencao()
        # Simular segundo save com os mesmos dados
        m.concluir_manutencao()
        qtd = DespesaVeiculo.objects.filter(veiculo=v, tipo='MANUTENCAO').count()
        self.assertEqual(qtd, 1)

    def test_despesa_manutencao_entra_no_balanco_mensal(self):
        from financeiro.models import BalancoMensal
        from tests.factories import criar_config_financeira
        criar_config_financeira()
        v = criar_veiculo()
        m = criar_manutencao(veiculo=v, concluida=False)
        m.concluir_manutencao()
        hoje = datetime.date.today()

        balanco = BalancoMensal.gerar_balanco(hoje.month, hoje.year)
        self.assertGreater(balanco.total_despesas_frota, Decimal('0.00'))


# ══════════════════════════════════════════════
# REGRAS DE NEGÓCIO ESPECÍFICAS
# (absorvidas de test_regras_negocio.py)
# ══════════════════════════════════════════════

class RegrasNegocioVeiculoTests(TestCase):
    """
    Regras de negócio que requerem desactivação temporária do signal
    criar_perfil_por_role para criar Motorista directamente.
    """

    def setUp(self):
        from django.db.models.signals import post_save
        from core.models import User
        from core.signals import criar_perfil_por_role

        post_save.disconnect(criar_perfil_por_role, sender=User)
        try:
            u = User.objects.create_user(
                email='mot_regras@bus.com', nome='Carlos Regras',
                role='MOTORISTA', password='pass123',
            )
            from core.models import Motorista as M
            self.motorista = M.objects.create(
                user=u,
                data_nascimento=datetime.date(1980, 1, 1),
                nrBI='100000000001A',
                carta_conducao='100000001',
                validade_da_carta=data_futura(365),
                salario=Decimal('15000.00'),
            )
            from transporte.models import Veiculo as V
            self.veiculo = V.objects.create(
                marca='Toyota', modelo='Coaster', matricula='RGR-001-MZ',
                capacidade=20, motorista=self.motorista,
                quilometragem_atual=1000,
                data_validade_seguro=data_futura(60),
                data_validade_inspecao=data_futura(60),
                data_validade_manifesto=data_futura(60),
                nr_manifesto='MANRG001',
            )
        finally:
            post_save.connect(criar_perfil_por_role, sender=User)

    def test_matricula_guardada_em_maiusculas(self):
        """Matrícula é normalizada para maiúsculas no save()."""
        from django.db.models.signals import post_save
        from core.models import User
        from core.signals import criar_perfil_por_role
        from transporte.models import Veiculo as V

        post_save.disconnect(criar_perfil_por_role, sender=User)
        try:
            u2 = User.objects.create_user(
                email='mot2_regras@bus.com', nome='Motorista Dois',
                role='MOTORISTA', password='pass123',
            )
            from core.models import Motorista as M
            m2 = M.objects.create(
                user=u2,
                data_nascimento=datetime.date(1985, 6, 15),
                nrBI='200000000002B',
                carta_conducao='200000002',
                validade_da_carta=data_futura(365),
                salario=Decimal('14000.00'),
            )
        finally:
            post_save.connect(criar_perfil_por_role, sender=User)

        v = V.objects.create(
            marca='Nissan', modelo='Urvan', matricula='xyz-789-gp',
            capacidade=15, motorista=m2,
            data_validade_seguro=data_futura(60),
            data_validade_inspecao=data_futura(60),
            data_validade_manifesto=data_futura(60),
            nr_manifesto='MANRG002',
        )
        self.assertEqual(v.matricula, 'XYZ-789-GP')

    def test_motorista_nao_pode_ter_dois_veiculos_ativos(self):
        """Um motorista não pode ser atribuído a dois veículos activos."""
        from django.core.exceptions import ValidationError
        from transporte.models import Veiculo as V
        with self.assertRaises(ValidationError):
            V.objects.create(
                marca='Ford', modelo='Transit', matricula='FOR-001-MC',
                capacidade=15, motorista=self.motorista, ativo=True,
                data_validade_seguro=data_futura(60),
                data_validade_inspecao=data_futura(60),
                data_validade_manifesto=data_futura(60),
                nr_manifesto='MANRG003',
            )

    def test_calculo_consumo_medio(self):
        """Consumo médio em KM/L calculado a partir dos abastecimentos."""
        from transporte.models import Abastecimento
        Abastecimento.objects.create(
            veiculo=self.veiculo, quilometragem_no_ato=1000,
            quantidade_litros=Decimal('50'), custo_total=Decimal('2500'),
            posto_combustivel='Posto Central',
        )
        Abastecimento.objects.create(
            veiculo=self.veiculo, quilometragem_no_ato=1500,
            quantidade_litros=Decimal('50'), custo_total=Decimal('2500'),
            posto_combustivel='Posto Central',
        )
        self.assertEqual(self.veiculo.consumo_medio(), 10.0)

    def test_alerta_manutencao_por_quilometragem(self):
        """precisa_manutencao() retorna True quando km ultrapassa o limite."""
        from transporte.models import Veiculo as V
        V.objects.filter(pk=self.veiculo.pk).update(quilometragem_atual=11000)
        self.veiculo.refresh_from_db()
        self.assertTrue(self.veiculo.precisa_manutencao())

    def test_rota_bloqueada_com_seguro_vencido(self):
        """Não é possível criar rota se o seguro do veículo estiver vencido."""
        from django.core.exceptions import ValidationError
        from transporte.models import Rota, Veiculo as V
        V.objects.filter(pk=self.veiculo.pk).update(
            data_validade_seguro=data_passada(1)
        )
        self.veiculo.refresh_from_db()
        rota = Rota(
            nome='Rota Bloqueada', veiculo=self.veiculo,
            hora_partida=datetime.time(6, 0),
            hora_chegada=datetime.time(7, 30),
        )
        with self.assertRaises(ValidationError) as cm:
            rota.full_clean()
        self.assertIn('inspecção vencida', str(cm.exception))

    def test_sincronizacao_km_abastecimento(self):
        """Abastecimento actualiza quilometragem do veículo automaticamente."""
        from transporte.models import Abastecimento
        Abastecimento.objects.create(
            veiculo=self.veiculo, quilometragem_no_ato=2500,
            quantidade_litros=Decimal('40'), custo_total=Decimal('2000'),
            posto_combustivel='Posto Norte',
        )
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.quilometragem_atual, 2500)


# ══════════════════════════════════════════════
# CHECK-IN ACTION
# ══════════════════════════════════════════════

class CheckInActionTests(BaseAPITestCase):
    """
    Testa o endpoint POST /transportes/{id}/check-in/
    — transições de estado PENDENTE → EMBARCADO → DESEMBARCADO.
    """

    def setUp(self):
        super().setUp()
        from tests.factories import criar_rota, criar_aluno, criar_config_financeira
        criar_config_financeira()
        self.rota = criar_rota()
        self.aluno = criar_aluno()
        self.rota.alunos.add(self.aluno)

    def _criar_registo(self):
        from transporte.models import TransporteAluno
        import datetime
        return TransporteAluno.objects.create(
            aluno=self.aluno,
            rota=self.rota,
            data=datetime.date.today(),
            status='PENDENTE',
        )

    def test_check_in_pendente_para_embarcado(self):
        """Motorista pode mover PENDENTE → EMBARCADO."""
        self.autenticar_como_motorista()
        registo = self._criar_registo()
        resp = self.client.post(
            f'/api/v1/transportes/{registo.pk}/check-in/',
            {'status': 'EMBARCADO'},
        )
        self.assertEqual(resp.status_code, 200)
        registo.refresh_from_db()
        self.assertEqual(registo.status, 'EMBARCADO')

    def test_check_in_embarcado_para_desembarcado(self):
        """Motorista pode mover EMBARCADO → DESEMBARCADO."""
        self.autenticar_como_motorista()
        registo = self._criar_registo()
        registo.status = 'EMBARCADO'
        registo.save()
        resp = self.client.post(
            f'/api/v1/transportes/{registo.pk}/check-in/',
            {'status': 'DESEMBARCADO'},
        )
        self.assertEqual(resp.status_code, 200)

    def test_check_in_transicao_invalida_rejeitada(self):
        """PENDENTE → DESEMBARCADO não é uma transição válida."""
        self.autenticar_como_motorista()
        registo = self._criar_registo()
        resp = self.client.post(
            f'/api/v1/transportes/{registo.pk}/check-in/',
            {'status': 'DESEMBARCADO'},
        )
        self.assertEqual(resp.status_code, 400)

    def test_check_in_sem_autenticacao_retorna_401(self):
        registo = self._criar_registo()
        resp = self.client.post(
            f'/api/v1/transportes/{registo.pk}/check-in/',
            {'status': 'EMBARCADO'},
        )
        self.assertEqual(resp.status_code, 401)

    def test_check_in_encarregado_sem_acesso(self):
        """Encarregado não pode fazer check-in."""
        self.autenticar_como_encarregado()
        registo = self._criar_registo()
        resp = self.client.post(
            f'/api/v1/transportes/{registo.pk}/check-in/',
            {'status': 'EMBARCADO'},
        )
        self.assertEqual(resp.status_code, 403)


# ══════════════════════════════════════════════
# FILTROS DE DATA — TRANSPORTE
# ══════════════════════════════════════════════

class FiltroDataTransporteTests(BaseAPITestCase):
    """Testa filtragem por intervalo de datas nos endpoints de transporte."""

    def setUp(self):
        super().setUp()
        from tests.factories import criar_rota, criar_aluno, criar_config_financeira
        criar_config_financeira()
        self.rota = criar_rota()
        self.aluno = criar_aluno()
        self.rota.alunos.add(self.aluno)

    def _criar_registo(self, data_str):
        from transporte.models import TransporteAluno
        import datetime
        return TransporteAluno.objects.create(
            aluno=self.aluno,
            rota=self.rota,
            data=datetime.date.fromisoformat(data_str),
            status='PENDENTE',
        )

    def test_filtro_data_min_abastecimento(self):
        self.autenticar_como_gestor()
        resp = self.client.get('/api/v1/transportes/?data_min=2025-06-01')
        self.assertEqual(resp.status_code, 200)

    def test_filtro_data_max_abastecimento(self):
        self.autenticar_como_gestor()
        r1 = self._criar_registo('2025-01-10')
        r2 = self._criar_registo('2025-06-10')
        resp = self.client.get('/api/v1/transportes/?data_max=2025-03-01')
        self.assertEqual(resp.status_code, 200)
        resultados = resp.data['results'] if 'results' in resp.data else resp.data
        ids = [r['id'] for r in resultados]
        self.assertIn(r1.pk, ids)
        self.assertNotIn(r2.pk, ids)
