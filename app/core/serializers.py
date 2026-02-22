from rest_framework import serializers
from core.models import Aluno, Motorista, Encarregado
from accounts.models import User
from accounts.serializers import UserSerializer as AccountUserSerializer


class CoreUserSerializer(serializers.ModelSerializer):
    """Serializer simplicado para exibir dados do utilizador dentro do core
    Renomeado para evitar comflitos com accounts.serializer.UserSerializer.
    """
    class Meta:
        model = User
        fields = [
            'id', 'nome', 'email', 'role', 'is_active',
        ]
        read_only_fields = ['id', 'role', 'is_active']


class EncarregadoSerializer(serializers.ModelSerializer):
    user = CoreUserSerializer(read_only=True)
    alunos = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Encarregado
        fields = [
            'id', 'user', 'nrBI', 'telefone', 'endereco', 'ativo', 'alunos', 'criado_em', 'atualizado_em',
        ]
        read_only_fields = ['id', 'criado_em', 'atualizado_em']


class AlunoSerializer(serializers.ModelSerializer):
    user = CoreUserSerializer(read_only=True)
    encarregado = EncarregadoSerializer(read_only=True)
    idade = serializers.ReadOnlyField(help_text="Idade Calculada do Aluno")

    class Meta:
        model = Aluno
        fields = [
            'id', 'user', 'encarregado', 'data_nascimento', 'nrBI',
            'escola_dest', 'classe', 'mensalidade', 'ativo', 'idade',
            'criado_em', 'atualizado_em',
        ]
        read_only_fields = ['id', 'idade', 'criado_em', 'atualizado_em']


class MotoristaSerializer(serializers.ModelSerializer):
    user = CoreUserSerializer(read_only=True)
    email = serializers.ReadOnlyField(source='user.email')
    idade = serializers.ReadOnlyField(help_text="Idade Calculada do Motorista")

    class Meta:
        model = Motorista
        fields = [
            'id', 'user', 'email', 'data_nascimento', 'idade', 'nrBI',
            'telefone', 'endereco', 'carta_conducao', 'validade_da_carta',
            'salario', 'ativo', 'criado_em', 'atualizado_em',
        ]
        read_only_fields = ['id', 'idade', 'criado_em', 'atualizado_em']
