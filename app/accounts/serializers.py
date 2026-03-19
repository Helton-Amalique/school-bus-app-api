from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from core.models import Aluno, Encarregado, Motorista, Gestor, Monitor
from datetime import date

User = get_user_model()


# ──────────────────────────────────────────────
# USER
# ──────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    """Leitura pública do utilizador — sem password, sem permissões."""

    class Meta:
        model = User
        fields = ['id', 'email', 'nome', 'role', 'is_active', 'data_criacao']
        read_only_fields = ['id', 'data_criacao']


class UserCreateSerializer(serializers.ModelSerializer):
    """Criação de utilizador com password e confirmação."""

    password  = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, label='Confirmar password', style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['email', 'nome', 'role', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': 'As passwords não coincidem.'})
        try:
            validate_password(data['password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    """Atualização de dados do utilizador — sem alteração de role nem password."""

    class Meta:
        model = User
        fields = ['nome', 'is_active']

    def validate_nome(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("O nome deve ter pelo menos 2 caracteres.")
        return value.strip().title()


class ChangePasswordSerializer(serializers.Serializer):
    """Alteração de password autenticada."""

    password_atual  = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_nova   = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_nova2  = serializers.CharField(write_only=True, label='Confirmar nova password', style={'input_type': 'password'})

    def validate(self, data):
        if data['password_nova'] != data['password_nova2']:
            raise serializers.ValidationError({'password_nova2': 'As passwords não coincidem.'})
        try:
            validate_password(data['password_nova'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password_nova': list(e.messages)})
        return data

    def validate_password_atual(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("A password atual está incorreta.")
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['password_nova'])
        user.save()
        return user


class EncarregadoSerializer(serializers.ModelSerializer):
    nome  = serializers.ReadOnlyField(source='user.nome')
    email = serializers.ReadOnlyField(source='user.email')

    class Meta:
        model = Encarregado
        fields = ['id', 'nome', 'email', 'nrBI', 'telefone', 'endereco', 'ativo']
        read_only_fields = ['id']


class EncarregadoCreateSerializer(serializers.ModelSerializer):
    """Criação de encarregado — cria o User e o perfil numa só operação."""

    email    = serializers.EmailField()
    nome     = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    class Meta:
        model = Encarregado
        fields = ['email', 'nome', 'password', 'nrBI', 'telefone', 'endereco']

    def validate_email(self, value):
        if User.objects.filter(email=value.lower().strip()).exists():
            raise serializers.ValidationError("Este email já está em uso.")
        return value.lower().strip()

    def create(self, validated_data):
        email    = validated_data.pop('email')
        nome     = validated_data.pop('nome')
        password = validated_data.pop('password')
        user = User.objects.create_user(
            email=email, nome=nome,
            role=User.Cargo.ENCARREGADO, password=password
        )
        return Encarregado.objects.create(user=user, **validated_data)


class AlunoSerializer(serializers.ModelSerializer):
    nome            = serializers.ReadOnlyField(source='user.nome')
    email           = serializers.ReadOnlyField(source='user.email')
    idade           = serializers.ReadOnlyField()
    acesso_bloqueado = serializers.SerializerMethodField()
    encarregado_nome = serializers.ReadOnlyField(source='encarregado.user.nome')

    class Meta:
        model = Aluno
        fields = [
            'id', 'nome', 'email', 'idade',
            'data_nascimento', 'nrBI',
            'escola_dest', 'classe', 'mensalidade',
            'encarregado', 'encarregado_nome',
            'acesso_bloqueado', 'ativo',
        ]
        read_only_fields = ['id']

    def get_acesso_bloqueado(self, obj) -> bool:
        return obj.tem_acesso_bloqueado()


class AlunoCreateSerializer(serializers.ModelSerializer):
    """Criação de aluno — cria o User e o perfil numa só operação."""

    email    = serializers.EmailField()
    nome     = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    class Meta:
        model = Aluno
        fields = [
            'email', 'nome', 'password',
            'data_nascimento', 'nrBI',
            'escola_dest', 'classe', 'mensalidade',
            'encarregado',
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value.lower().strip()).exists():
            raise serializers.ValidationError("Este email já está em uso.")
        return value.lower().strip()

    def validate_data_nascimento(self, value):
        if value > date.today():
            raise serializers.ValidationError("A data de nascimento não pode ser no futuro.")
        hoje = date.today()
        idade = hoje.year - value.year - ((hoje.month, hoje.day) < (value.month, value.day))
        if idade < 3:
            raise serializers.ValidationError("O aluno deve ter pelo menos 3 anos.")
        return value

    def create(self, validated_data):
        email    = validated_data.pop('email')
        nome     = validated_data.pop('nome')
        password = validated_data.pop('password')
        user = User.objects.create_user(
            email=email, nome=nome,
            role=User.Cargo.ALUNO, password=password
        )
        return Aluno.objects.create(user=user, **validated_data)


class MotoristaSerializer(serializers.ModelSerializer):
    nome                 = serializers.ReadOnlyField(source='user.nome')
    email                = serializers.ReadOnlyField(source='user.email')
    idade                = serializers.ReadOnlyField()
    carta_vencida        = serializers.SerializerMethodField()
    estado_carta         = serializers.SerializerMethodField()

    class Meta:
        model = Motorista
        fields = [
            'id', 'nome', 'email', 'idade',
            'data_nascimento', 'nrBI',
            'telefone', 'endereco',
            'carta_conducao', 'validade_da_carta',
            'carta_vencida', 'estado_carta',
            'salario', 'ativo',
        ]
        read_only_fields = ['id']

    def get_carta_vencida(self, obj) -> bool:
        return obj.carta_conducao_vencida()

    def get_estado_carta(self, obj) -> str:
        if not obj.validade_da_carta:
            return "sem_data"
        if obj.carta_conducao_vencida():
            return "vencida"
        if (obj.validade_da_carta - date.today()).days <= 30:
            return "expira_em_breve"
        return "valida"


class MotoristaCreateSerializer(serializers.ModelSerializer):
    email    = serializers.EmailField()
    nome     = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    class Meta:
        model = Motorista
        fields = [
            'email', 'nome', 'password',
            'data_nascimento', 'nrBI',
            'telefone', 'endereco',
            'carta_conducao', 'validade_da_carta',
            'salario',
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value.lower().strip()).exists():
            raise serializers.ValidationError("Este email já está em uso.")
        return value.lower().strip()

    def validate_data_nascimento(self, value):
        if value > date.today():
            raise serializers.ValidationError("A data de nascimento não pode ser no futuro.")
        hoje = date.today()
        idade = hoje.year - value.year - ((hoje.month, hoje.day) < (value.month, value.day))
        if idade < 18:
            raise serializers.ValidationError("O motorista deve ter pelo menos 18 anos.")
        return value

    def validate_validade_da_carta(self, value):
        if value and value < date.today():
            raise serializers.ValidationError("A carta de condução está expirada.")
        return value

    def create(self, validated_data):
        email    = validated_data.pop('email')
        nome     = validated_data.pop('nome')
        password = validated_data.pop('password')
        user = User.objects.create_user(
            email=email, nome=nome,
            role=User.Cargo.MOTORISTA, password=password
        )
        return Motorista.objects.create(user=user, **validated_data)


class GestorSerializer(serializers.ModelSerializer):
    nome                    = serializers.ReadOnlyField(source='user.nome')
    email                   = serializers.ReadOnlyField(source='user.email')
    idade                   = serializers.ReadOnlyField()
    pode_aprovar_manutencao = serializers.SerializerMethodField()
    total_motoristas        = serializers.SerializerMethodField()

    class Meta:
        model = Gestor
        fields = [
            'id', 'nome', 'email', 'idade',
            'data_nascimento', 'nrBI',
            'telefone', 'endereco',
            'departamento', 'salario',
            'motoristas_supervisionados',
            'pode_aprovar_manutencao',
            'total_motoristas',
            'ativo',
        ]
        read_only_fields = ['id']

    def get_pode_aprovar_manutencao(self, obj) -> bool:
        return obj.pode_aprovar_manutencao()

    def get_total_motoristas(self, obj) -> int:
        return obj.motoristas_supervisionados.count()


class GestorCreateSerializer(serializers.ModelSerializer):
    email    = serializers.EmailField()
    nome     = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    class Meta:
        model = Gestor
        fields = [
            'email', 'nome', 'password',
            'data_nascimento', 'nrBI',
            'telefone', 'endereco',
            'departamento', 'salario',
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value.lower().strip()).exists():
            raise serializers.ValidationError("Este email já está em uso.")
        return value.lower().strip()

    def validate_data_nascimento(self, value):
        if value > date.today():
            raise serializers.ValidationError("A data de nascimento não pode ser no futuro.")
        hoje = date.today()
        idade = hoje.year - value.year - ((hoje.month, hoje.day) < (value.month, value.day))
        if idade < 18:
            raise serializers.ValidationError("O gestor deve ter pelo menos 18 anos.")
        return value

    def create(self, validated_data):
        email    = validated_data.pop('email')
        nome     = validated_data.pop('nome')
        password = validated_data.pop('password')
        user = User.objects.create_user(
            email=email, nome=nome,
            role=User.Cargo.GESTOR, password=password
        )
        return Gestor.objects.create(user=user, **validated_data)


class MonitorSerializer(serializers.ModelSerializer):
    nome       = serializers.ReadOnlyField(source='user.nome')
    email      = serializers.ReadOnlyField(source='user.email')
    idade      = serializers.ReadOnlyField()
    rota_ativa = serializers.SerializerMethodField()

    class Meta:
        model = Monitor
        fields = [
            'id', 'nome', 'email', 'idade',
            'data_nascimento', 'nrBI',
            'telefone', 'endereco',
            'salario', 'rota_ativa', 'ativo',
        ]
        read_only_fields = ['id']

    def get_rota_ativa(self, obj) -> dict | None:
        rota = obj.rota_ativa
        if not rota:
            return None
        return {
            'id': rota.pk,
            'nome': rota.nome,
            'hora_partida': rota.hora_partida,
            'hora_chegada': rota.hora_chegada,
        }


class MonitorCreateSerializer(serializers.ModelSerializer):
    email    = serializers.EmailField()
    nome     = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    class Meta:
        model = Monitor
        fields = [
            'email', 'nome', 'password',
            'data_nascimento', 'nrBI',
            'telefone', 'endereco', 'salario',
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value.lower().strip()).exists():
            raise serializers.ValidationError("Este email já está em uso.")
        return value.lower().strip()

    def validate_data_nascimento(self, value):
        if value > date.today():
            raise serializers.ValidationError("A data de nascimento não pode ser no futuro.")
        hoje = date.today()
        idade = hoje.year - value.year - ((hoje.month, hoje.day) < (value.month, value.day))
        if idade < 18:
            raise serializers.ValidationError("O monitor deve ter pelo menos 18 anos.")
        return value

    def create(self, validated_data):
        email    = validated_data.pop('email')
        nome     = validated_data.pop('nome')
        password = validated_data.pop('password')
        user = User.objects.create_user(
            email=email, nome=nome,
            role=User.Cargo.MONITOR, password=password
        )
        return Monitor.objects.create(user=user, **validated_data)
