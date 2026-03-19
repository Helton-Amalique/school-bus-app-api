"""
tests/factories.py
==================
Factories centrais para todos os módulos de teste.

Uso:
  from tests.factories import (
      criar_user, criar_aluno, criar_motorista,
      criar_veiculo, criar_rota, criar_config_financeira,
  )

Todas as factories aceitam kwargs para sobrescrever valores por omissão,
permitindo criar variantes facilmente nos testes.
"""

import datetime
from decimal import Decimal

from django.utils import timezone


# ──────────────────────────────────────────────
# DATAS UTILITÁRIAS
# ──────────────────────────────────────────────

def data_nascimento_adulto():
    return datetime.date.today().replace(year=datetime.date.today().year - 30)

def data_nascimento_aluno():
    return datetime.date.today().replace(year=datetime.date.today().year - 10)

def data_futura(dias=365):
    return datetime.date.today() + datetime.timedelta(days=dias)

def data_passada(dias=30):
    return datetime.date.today() - datetime.timedelta(days=dias)


# ──────────────────────────────────────────────
# CORE
# ──────────────────────────────────────────────

def criar_user(role='GESTOR', email=None, nome='Utilizador Teste', **kwargs):
    from core.models import User
    if email is None:
        email = f'{role.lower()}_{timezone.now().timestamp():.0f}@teste.co.mz'

    return User.objects.create_user(
        email=email,
        password='Senha@1234',
        nome=nome,
        role=role,
        **kwargs
    )


def criar_encarregado(user=None, **kwargs):
    from core.models import Encarregado
    if user is None:
        user = criar_user(role='ENCARREGADO')

    defaults = {
        'user': user,
        'data_nascimento': data_nascimento_adulto(),
        'nrBI': f'{abs(hash(user.email)) % 999999999999:012d}A',
    }
    defaults.update(kwargs)
    return Encarregado.objects.create(**defaults)


def criar_aluno(encarregado=None, user=None, **kwargs):
    from core.models import Aluno

    if encarregado is None:
        encarregado = criar_encarregado()
    if user is None:
        user = criar_user(role='ALUNO')

    defaults = {
        'user': user,
        'encarregado': encarregado,
        'data_nascimento': data_nascimento_aluno(),
        'nrBI': f'{abs(hash(user.email)) % 999999999999:012d}A',
        'escola_dest': 'Escola Primária Central',
        'classe': '5ª Classe',
        'mensalidade': Decimal('2500.00'),
    }
    defaults.update(kwargs)
    return Aluno.objects.create(**defaults)


def criar_motorista(user=None, **kwargs):
    from core.models import Motorista

    if user is None:
        user = criar_user(role='MOTORISTA')

    ts = abs(hash(user.email)) % 999999999
    defaults = {
        'user': user,
        'data_nascimento': data_nascimento_adulto(),
        'nrBI': f'{ts:012d}A',
        'carta_conducao': f'{ts % 999999999:09d}',
        'validade_da_carta': data_futura(365),
        'salario': Decimal('15000.00'),
    }
    defaults.update(kwargs)
    return Motorista.objects.create(**defaults)


def criar_gestor(user=None, departamento='GERAL', **kwargs):
    from core.models import Gestor

    if user is None:
        user = criar_user(role='GESTOR')

    ts = abs(hash(user.email)) % 999999999
    defaults = {
        'user': user,
        'data_nascimento': data_nascimento_adulto(),
        'nrBI': f'{ts:012d}A',
        'departamento': departamento,
        'salario': Decimal('25000.00'),
    }
    defaults.update(kwargs)
    return Gestor.objects.create(**defaults)


def criar_monitor(user=None, **kwargs):
    from core.models import Monitor

    if user is None:
        user = criar_user(role='MONITOR')

    ts = abs(hash(user.email)) % 999999999
    defaults = {
        'user': user,
        'data_nascimento': data_nascimento_adulto(),
        'nrBI': f'{ts:012d}A',
        'salario': Decimal('8000.00'),
    }
    defaults.update(kwargs)
    return Monitor.objects.create(**defaults)


# ──────────────────────────────────────────────
# TRANSPORTE
# ──────────────────────────────────────────────

def criar_veiculo(motorista=None, **kwargs):
    from transporte.models import Veiculo

    if motorista is None:
        motorista = criar_motorista()

    ts = abs(hash(str(motorista.pk))) % 999
    defaults = {
        'marca': 'Toyota',
        'modelo': 'Hiace',
        'matricula': f'ABC-{ts:03d}-XY',
        'capacidade': 15,
        'motorista': motorista,
        'data_validade_seguro': data_futura(365),
        'data_validade_inspecao': data_futura(365),
        'data_validade_manifesto': data_futura(365),
        'nr_manifesto': f'MAN{ts:05d}',
    }
    defaults.update(kwargs)
    return Veiculo.objects.create(**defaults)


def criar_rota(veiculo=None, alunos=None, **kwargs):
    from transporte.models import Rota

    if veiculo is None:
        veiculo = criar_veiculo()

    defaults = {
        'nome': 'Rota Centro',
        'veiculo': veiculo,
        'hora_partida': datetime.time(6, 0),
        'hora_chegada': datetime.time(7, 30),
    }
    defaults.update(kwargs)
    rota = Rota.objects.create(**defaults)

    if alunos:
        rota.alunos.set(alunos)

    return rota


def criar_transporte_aluno(aluno=None, rota=None, status='PENDENTE', **kwargs):
    from transporte.models import TransporteAluno

    if aluno is None:
        aluno = criar_aluno()
    if rota is None:
        rota = criar_rota()
        rota.alunos.add(aluno)

    defaults = {
        'aluno': aluno,
        'rota': rota,
        'status': status,
        'data': datetime.date.today(),
    }
    defaults.update(kwargs)
    return TransporteAluno.objects.create(**defaults)


def criar_manutencao(veiculo=None, concluida=False, **kwargs):
    from transporte.models import Manutencao

    if veiculo is None:
        veiculo = criar_veiculo()

    defaults = {
        'veiculo': veiculo,
        'tipo': 'PREVENTIVA',
        'descricao': 'Troca de óleo',
        'data_inicio': datetime.date.today(),
        'concluida': concluida,
        'custo': Decimal('5000.00'),
        'quilometragem_no_momento_revisao': 0,
    }
    defaults.update(kwargs)
    return Manutencao.objects.create(**defaults)


# ──────────────────────────────────────────────
# FINANCEIRO
# ──────────────────────────────────────────────

def criar_config_financeira(**kwargs):
    from financeiro.models import ConfiguracaoFinanceira

    defaults = {
        'dia_vencimento': 5,
        'dia_limite_pagamento': 10,
        'valor_multa_fixa': Decimal('500.00'),
    }
    defaults.update(kwargs)
    obj, _ = ConfiguracaoFinanceira.objects.get_or_create(pk=1, defaults=defaults)
    return obj


def criar_categoria(nome='Mensalidade', tipo='RECEITA', **kwargs):
    from financeiro.models import Categoria

    obj, _ = Categoria.objects.get_or_create(nome=nome, tipo=tipo, **kwargs)
    return obj


def criar_mensalidade(aluno=None, mes_referente=None, **kwargs):
    from financeiro.models import Mensalidade

    if aluno is None:
        aluno = criar_aluno()

    if mes_referente is None:
        hoje = datetime.date.today()
        mes_referente = hoje.replace(day=1)

    defaults = {
        'aluno': aluno,
        'mes_referente': mes_referente,
        'valor': aluno.mensalidade,
        'estado': 'PENDENTE',
        'data_vencimento': mes_referente.replace(day=5),
    }
    defaults.update(kwargs)
    return Mensalidade.objects.create(**defaults)


def criar_funcionario(motorista=None, **kwargs):
    from financeiro.models import Funcionario

    if motorista is None:
        motorista = criar_motorista()

    defaults = {
        'motorista_perfil': motorista,
        'cargo': 'MOTORISTA',
        'salario_base': motorista.salario,
        'data_admissao': data_passada(180),
        'ativo': True,
    }
    defaults.update(kwargs)
    return Funcionario.objects.create(**defaults)
