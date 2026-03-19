
"""
core/serializers.py — CORRIGIDO
"""

from django.db import transaction
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from core.models import Aluno, Encarregado, Gestor, Monitor, Motorista, User


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'nome', 'nome_curto',
            'role', 'role_display',
            'is_active', 'data_criacao',
        )
        read_only_fields = fields


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label='Confirmar senha')

    class Meta:
        model = User
        fields = ('email', 'nome', 'role', 'password', 'password2')

    def validate(self, data):
        if data['password'] != data.pop('password2'):
            raise serializers.ValidationError({'password2': 'As senhas não coincidem.'})
        validate_password(data['password'])
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('nome', 'is_active')


class ChangePasswordSerializer(serializers.Serializer):
    senha_atual = serializers.CharField(write_only=True)
    nova_senha = serializers.CharField(write_only=True, min_length=8)
    nova_senha2 = serializers.CharField(write_only=True, label='Confirmar nova senha')

    def validate(self, data):
        if data['nova_senha'] != data['nova_senha2']:
            raise serializers.ValidationError({'nova_senha2': 'As senhas não coincidem.'})
        validate_password(data['nova_senha'])
        return data

    def validate_senha_atual(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Senha actual incorrecta.')
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['nova_senha'])
        user.save()
        return user


class PerfilReadMixin(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    idade = serializers.IntegerField(read_only=True)

    PERFIL_READ_FIELDS = (
        'id', 'user', 'data_nascimento', 'idade',
        'nrBI', 'telefone', 'endereco',
        'ativo', 'criado_em', 'atualizado_em',
    )


# ── helper interno ────────────────────────────────────────────────────────────

def _criar_user_de_validated(user_data: dict, role) -> User:
    """
    Cria um User a partir de dados já validados pelo UserCreateSerializer nested.

    O validate() do UserCreateSerializer já removeu 'password2' com pop().
    Chamar UserCreateSerializer(data=user_data).is_valid() de novo falharia
    porque 'password2' já não existe nos dados.
    """
    user_data['role'] = role
    password = user_data.pop('password')
    user = User(**user_data)
    user.set_password(password)
    user.save()
    return user


# ── ENCARREGADO ───────────────────────────────────────────────────────────────

class EncarregadoSerializer(PerfilReadMixin):
    total_alunos = serializers.SerializerMethodField()

    class Meta:
        model = Encarregado
        fields = PerfilReadMixin.PERFIL_READ_FIELDS + ('total_alunos',)

    def get_total_alunos(self, obj):
        return obj.alunos.count()


class EncarregadoWriteSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer(required=False)

    class Meta:
        model = Encarregado
        fields = ('user', 'data_nascimento', 'nrBI', 'telefone', 'endereco', 'ativo')

    def validate(self, data):
        if not self.instance and not data.get('user'):
            raise serializers.ValidationError({'user': 'Os dados do utilizador são obrigatórios.'})
        return data

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = _criar_user_de_validated(user_data, User.Cargo.ENCARREGADO)
        return Encarregado.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if user_data:
            ser = UserUpdateSerializer(instance.user, data=user_data, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        return instance


# ── ALUNO ─────────────────────────────────────────────────────────────────────

class AlunoSerializer(PerfilReadMixin):
    encarregado = EncarregadoSerializer(read_only=True)

    class Meta:
        model = Aluno
        fields = PerfilReadMixin.PERFIL_READ_FIELDS + (
            'encarregado', 'escola_dest', 'classe', 'mensalidade',
        )


class AlunoWriteSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer(required=False)

    class Meta:
        model = Aluno
        fields = (
            'user', 'encarregado',
            'data_nascimento', 'nrBI', 'telefone', 'endereco',
            'escola_dest', 'classe', 'mensalidade', 'ativo',
        )

    def validate_encarregado(self, value):
        if not value.ativo:
            raise serializers.ValidationError('O encarregado seleccionado está inactivo.')
        return value

    def validate(self, data):
        if not self.instance and not data.get('user'):
            raise serializers.ValidationError({'user': 'Os dados do utilizador são obrigatórios.'})
        return data

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = _criar_user_de_validated(user_data, User.Cargo.ALUNO)
        return Aluno.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if user_data:
            ser = UserUpdateSerializer(instance.user, data=user_data, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        return instance


class AlunoListSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(source='user.nome', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    encarregado_nome = serializers.CharField(source='encarregado.user.nome', read_only=True)

    class Meta:
        model = Aluno
        fields = (
            'id', 'nome', 'email',
            'escola_dest', 'classe', 'mensalidade',
            'encarregado_nome', 'ativo',
        )


# ── MOTORISTA ─────────────────────────────────────────────────────────────────

class MotoristaSerializer(PerfilReadMixin):
    carta_vencida = serializers.BooleanField(source='carta_conducao_vencida', read_only=True)

    class Meta:
        model = Motorista
        fields = PerfilReadMixin.PERFIL_READ_FIELDS + (
            'carta_conducao', 'validade_da_carta', 'carta_vencida', 'salario',
        )


class MotoristaWriteSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer(required=False)

    class Meta:
        model = Motorista
        fields = (
            'user',
            'data_nascimento', 'nrBI', 'telefone', 'endereco',
            'carta_conducao', 'validade_da_carta', 'salario', 'ativo',
        )

    def validate(self, data):
        if not self.instance and not data.get('user'):
            raise serializers.ValidationError({'user': 'Os dados do utilizador são obrigatórios.'})
        return data

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = _criar_user_de_validated(user_data, User.Cargo.MOTORISTA)
        return Motorista.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if user_data:
            ser = UserUpdateSerializer(instance.user, data=user_data, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        return instance


class MotoristaListSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(source='user.nome', read_only=True)
    carta_vencida = serializers.BooleanField(source='carta_conducao_vencida', read_only=True)

    class Meta:
        model = Motorista
        fields = ('id', 'nome', 'carta_conducao', 'validade_da_carta', 'carta_vencida', 'ativo')


# ── GESTOR ────────────────────────────────────────────────────────────────────

class GestorSerializer(PerfilReadMixin):
    departamento_display = serializers.CharField(source='get_departamento_display', read_only=True)
    pode_aprovar_manutencao = serializers.BooleanField(read_only=True)
    pode_aprovar_abastecimento = serializers.BooleanField(read_only=True)
    motoristas_supervisionados = MotoristaListSerializer(many=True, read_only=True)

    class Meta:
        model  = Gestor
        fields = PerfilReadMixin.PERFIL_READ_FIELDS + (
            'departamento', 'departamento_display', 'salario',
            'pode_aprovar_manutencao', 'pode_aprovar_abastecimento',
            'motoristas_supervisionados',
        )


class GestorWriteSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer(required=False)
    motoristas_supervisionados = serializers.PrimaryKeyRelatedField(
        queryset=Motorista.objects.filter(ativo=True),
        many=True, required=False,
    )

    class Meta:
        model = Gestor
        fields = (
            'user',
            'data_nascimento', 'nrBI', 'telefone', 'endereco',
            'departamento', 'salario', 'ativo',
            'motoristas_supervisionados',
        )

    def validate(self, data):
        if not self.instance and not data.get('user'):
            raise serializers.ValidationError({'user': 'Os dados do utilizador são obrigatórios.'})
        return data

    @transaction.atomic
    def create(self, validated_data):
        motoristas = validated_data.pop('motoristas_supervisionados', [])
        user_data = validated_data.pop('user')
        user = _criar_user_de_validated(user_data, User.Cargo.GESTOR)
        gestor = Gestor.objects.create(user=user, **validated_data)
        gestor.motoristas_supervisionados.set(motoristas)
        return gestor

    @transaction.atomic
    def update(self, instance, validated_data):
        motoristas = validated_data.pop('motoristas_supervisionados', None)
        user_data = validated_data.pop('user', {})
        if user_data:
            ser = UserUpdateSerializer(instance.user, data=user_data, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if motoristas is not None:
            instance.motoristas_supervisionados.set(motoristas)
        return instance


# ── MONITOR ───────────────────────────────────────────────────────────────────

class MonitorSerializer(PerfilReadMixin):
    tem_rota_ativa = serializers.BooleanField(read_only=True)
    rota_ativa_nome = serializers.SerializerMethodField()

    class Meta:
        model = Monitor
        fields = PerfilReadMixin.PERFIL_READ_FIELDS + (
            'salario', 'tem_rota_ativa', 'rota_ativa_nome',
        )

    def get_rota_ativa_nome(self, obj):
        rota = obj.rota_ativa
        return str(rota) if rota else None


class MonitorWriteSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer(required=False)

    class Meta:
        model = Monitor
        fields = (
            'user',
            'data_nascimento', 'nrBI', 'telefone', 'endereco',
            'salario', 'ativo',
        )

    def validate(self, data):
        if not self.instance and not data.get('user'):
            raise serializers.ValidationError({'user': 'Os dados do utilizador são obrigatórios.'})
        return data

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = _criar_user_de_validated(user_data, User.Cargo.MONITOR)
        return Monitor.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if user_data:
            ser = UserUpdateSerializer(instance.user, data=user_data, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        return instance


class MonitorListSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(source='user.nome', read_only=True)
    tem_rota_ativa = serializers.BooleanField(read_only=True)

    class Meta:
        model = Monitor
        fields = ('id', 'nome', 'salario', 'tem_rota_ativa', 'ativo')


# """
# core/serializers.py
# """

# from django.db import transaction
# from rest_framework import serializers
# from django.contrib.auth.password_validation import validate_password
# from core.models import Aluno, Encarregado, Gestor, Monitor, Motorista, User


# class UserSerializer(serializers.ModelSerializer):
#     role_display = serializers.CharField(source='get_role_display', read_only=True)

#     class Meta:
#         model = User
#         fields = (
#             'id', 'email', 'nome', 'nome_curto',
#             'role', 'role_display',
#             'is_active', 'data_criacao',
#         )
#         read_only_fields = fields


# class UserCreateSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, min_length=8)
#     password2 = serializers.CharField(write_only=True, label='Confirmar senha')

#     class Meta:
#         model = User
#         fields = ('email', 'nome', 'role', 'password', 'password2')

#     def validate(self, data):
#         if data['password'] != data.pop('password2'):
#             raise serializers.ValidationError({'password2': 'As senhas não coincidem.'})
#         validate_password(data['password'])
#         return data

#     def create(self, validated_data):
#         password = validated_data.pop('password')
#         user = User(**validated_data)
#         user.set_password(password)
#         user.save()
#         return user


# class UserUpdateSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ('nome', 'is_active')


# class ChangePasswordSerializer(serializers.Serializer):
#     senha_atual = serializers.CharField(write_only=True)
#     nova_senha = serializers.CharField(write_only=True, min_length=8)
#     nova_senha2 = serializers.CharField(write_only=True, label='Confirmar nova senha')

#     def validate(self, data):
#         if data['nova_senha'] != data['nova_senha2']:
#             raise serializers.ValidationError({'nova_senha2': 'As senhas não coincidem.'})
#         validate_password(data['nova_senha'])
#         return data

#     def validate_senha_atual(self, value):
#         user = self.context['request'].user
#         if not user.check_password(value):
#             raise serializers.ValidationError('Senha actual incorrecta.')
#         return value

#     def save(self, **kwargs):
#         user = self.context['request'].user
#         user.set_password(self.validated_data['nova_senha'])
#         user.save()
#         return user


# class PerfilReadMixin(serializers.ModelSerializer):
#     user = UserSerializer(read_only=True)
#     idade = serializers.IntegerField(read_only=True)

#     PERFIL_READ_FIELDS = (
#         'id', 'user', 'data_nascimento', 'idade',
#         'nrBI', 'telefone', 'endereco',
#         'ativo', 'criado_em', 'atualizado_em',
#     )


# # ── helper interno ────────────────────────────────────────────────────────────

# def _criar_user_de_validated(user_data: dict, role) -> User:
#     """
#     Cria um User a partir de dados já validados pelo UserCreateSerializer nested.

#     O validate() do UserCreateSerializer já removeu 'password2' com pop().
#     Chamar UserCreateSerializer(data=user_data).is_valid() de novo falharia
#     porque 'password2' já não existe nos dados.
#     """
#     user_data['role'] = role
#     password = user_data.pop('password')
#     user = User(**user_data)
#     user.set_password(password)
#     user.save()
#     return user


# # ── ENCARREGADO ───────────────────────────────────────────────────────────────

# class EncarregadoSerializer(PerfilReadMixin):
#     total_alunos = serializers.SerializerMethodField()

#     class Meta:
#         model = Encarregado
#         fields = PerfilReadMixin.PERFIL_READ_FIELDS + ('total_alunos',)

#     def get_total_alunos(self, obj):
#         return obj.alunos.count()


# class EncarregadoWriteSerializer(serializers.ModelSerializer):
#     user = UserCreateSerializer(required=False)

#     class Meta:
#         model = Encarregado
#         fields = ('user', 'data_nascimento', 'nrBI', 'telefone', 'endereco', 'ativo')

#     def validate(self, data):
#         if not self.instance and not data.get('user'):
#             raise serializers.ValidationError({'user': 'Os dados do utilizador são obrigatórios.'})
#         return data

#     @transaction.atomic
#     def create(self, validated_data):
#         user_data = validated_data.pop('user')
#         user = _criar_user_de_validated(user_data, User.Cargo.ENCARREGADO)
#         return Encarregado.objects.create(user=user, **validated_data)

#     @transaction.atomic
#     def update(self, instance, validated_data):
#         user_data = validated_data.pop('user', {})
#         if user_data:
#             UserUpdateSerializer(instance.user, data=user_data, partial=True).save()
#         for attr, val in validated_data.items():
#             setattr(instance, attr, val)
#         instance.save()
#         return instance


# # ── ALUNO ─────────────────────────────────────────────────────────────────────

# class AlunoSerializer(PerfilReadMixin):
#     encarregado = EncarregadoSerializer(read_only=True)

#     class Meta:
#         model = Aluno
#         fields = PerfilReadMixin.PERFIL_READ_FIELDS + (
#             'encarregado', 'escola_dest', 'classe', 'mensalidade',
#         )


# class AlunoWriteSerializer(serializers.ModelSerializer):
#     user = UserCreateSerializer(required=False)

#     class Meta:
#         model = Aluno
#         fields = (
#             'user', 'encarregado',
#             'data_nascimento', 'nrBI', 'telefone', 'endereco',
#             'escola_dest', 'classe', 'mensalidade', 'ativo',
#         )

#     def validate_encarregado(self, value):
#         if not value.ativo:
#             raise serializers.ValidationError('O encarregado seleccionado está inactivo.')
#         return value

#     def validate(self, data):
#         if not self.instance and not data.get('user'):
#             raise serializers.ValidationError({'user': 'Os dados do utilizador são obrigatórios.'})
#         return data

#     @transaction.atomic
#     def create(self, validated_data):
#         user_data = validated_data.pop('user')
#         user = _criar_user_de_validated(user_data, User.Cargo.ALUNO)
#         return Aluno.objects.create(user=user, **validated_data)

#     @transaction.atomic
#     def update(self, instance, validated_data):
#         user_data = validated_data.pop('user', {})
#         if user_data:
#             UserUpdateSerializer(instance.user, data=user_data, partial=True).save()
#         for attr, val in validated_data.items():
#             setattr(instance, attr, val)
#         instance.save()
#         return instance


# class AlunoListSerializer(serializers.ModelSerializer):
#     nome = serializers.CharField(source='user.nome',            read_only=True)
#     email = serializers.CharField(source='user.email',           read_only=True)
#     encarregado_nome = serializers.CharField(source='encarregado.user.nome', read_only=True)

#     class Meta:
#         model = Aluno
#         fields = (
#             'id', 'nome', 'email',
#             'escola_dest', 'classe', 'mensalidade',
#             'encarregado_nome', 'ativo',
#         )


# # ── MOTORISTA ─────────────────────────────────────────────────────────────────

# class MotoristaSerializer(PerfilReadMixin):
#     carta_vencida = serializers.BooleanField(source='carta_conducao_vencida', read_only=True)

#     class Meta:
#         model = Motorista
#         fields = PerfilReadMixin.PERFIL_READ_FIELDS + (
#             'carta_conducao', 'validade_da_carta', 'carta_vencida', 'salario',
#         )


# class MotoristaWriteSerializer(serializers.ModelSerializer):
#     user = UserCreateSerializer(required=False)

#     class Meta:
#         model = Motorista
#         fields = (
#             'user',
#             'data_nascimento', 'nrBI', 'telefone', 'endereco',
#             'carta_conducao', 'validade_da_carta', 'salario', 'ativo',
#         )

#     def validate(self, data):
#         if not self.instance and not data.get('user'):
#             raise serializers.ValidationError({'user': 'Os dados do utilizador são obrigatórios.'})
#         return data

#     @transaction.atomic
#     def create(self, validated_data):
#         user_data = validated_data.pop('user')
#         user = _criar_user_de_validated(user_data, User.Cargo.MOTORISTA)
#         return Motorista.objects.create(user=user, **validated_data)

#     @transaction.atomic
#     def update(self, instance, validated_data):
#         user_data = validated_data.pop('user', {})
#         if user_data:
#             UserUpdateSerializer(instance.user, data=user_data, partial=True).save()
#         for attr, val in validated_data.items():
#             setattr(instance, attr, val)
#         instance.save()
#         return instance


# class MotoristaListSerializer(serializers.ModelSerializer):
#     nome = serializers.CharField(source='user.nome',            read_only=True)
#     carta_vencida = serializers.BooleanField(source='carta_conducao_vencida', read_only=True)

#     class Meta:
#         model = Motorista
#         fields = ('id', 'nome', 'carta_conducao', 'validade_da_carta', 'carta_vencida', 'ativo')


# # ── GESTOR ────────────────────────────────────────────────────────────────────

# class GestorSerializer(PerfilReadMixin):
#     departamento_display = serializers.CharField(source='get_departamento_display', read_only=True)
#     pode_aprovar_manutencao = serializers.BooleanField(read_only=True)
#     pode_aprovar_abastecimento = serializers.BooleanField(read_only=True)
#     motoristas_supervisionados = MotoristaListSerializer(many=True, read_only=True)

#     class Meta:
#         model = Gestor
#         fields = PerfilReadMixin.PERFIL_READ_FIELDS + (
#             'departamento', 'departamento_display', 'salario',
#             'pode_aprovar_manutencao', 'pode_aprovar_abastecimento',
#             'motoristas_supervisionados',
#         )


# class GestorWriteSerializer(serializers.ModelSerializer):
#     user = UserCreateSerializer(required=False)
#     motoristas_supervisionados = serializers.PrimaryKeyRelatedField(
#         queryset=Motorista.objects.filter(ativo=True),
#         many=True, required=False,
#     )

#     class Meta:
#         model = Gestor
#         fields = (
#             'user',
#             'data_nascimento', 'nrBI', 'telefone', 'endereco',
#             'departamento', 'salario', 'ativo',
#             'motoristas_supervisionados',
#         )

#     def validate(self, data):
#         if not self.instance and not data.get('user'):
#             raise serializers.ValidationError({'user': 'Os dados do utilizador são obrigatórios.'})
#         return data

#     @transaction.atomic
#     def create(self, validated_data):
#         motoristas = validated_data.pop('motoristas_supervisionados', [])
#         user_data = validated_data.pop('user')
#         user = _criar_user_de_validated(user_data, User.Cargo.GESTOR)
#         gestor = Gestor.objects.create(user=user, **validated_data)
#         gestor.motoristas_supervisionados.set(motoristas)
#         return gestor

#     @transaction.atomic
#     def update(self, instance, validated_data):
#         motoristas = validated_data.pop('motoristas_supervisionados', None)
#         user_data = validated_data.pop('user', {})
#         if user_data:
#             UserUpdateSerializer(instance.user, data=user_data, partial=True).save()
#         for attr, val in validated_data.items():
#             setattr(instance, attr, val)
#         instance.save()
#         if motoristas is not None:
#             instance.motoristas_supervisionados.set(motoristas)
#         return instance


# # ── MONITOR ───────────────────────────────────────────────────────────────────

# class MonitorSerializer(PerfilReadMixin):
#     tem_rota_ativa = serializers.BooleanField(read_only=True)
#     rota_ativa_nome = serializers.SerializerMethodField()

#     class Meta:
#         model = Monitor
#         fields = PerfilReadMixin.PERFIL_READ_FIELDS + (
#             'salario', 'tem_rota_ativa', 'rota_ativa_nome',
#         )

#     def get_rota_ativa_nome(self, obj):
#         rota = obj.rota_ativa
#         return str(rota) if rota else None


# class MonitorWriteSerializer(serializers.ModelSerializer):
#     user = UserCreateSerializer(required=False)

#     class Meta:
#         model = Monitor
#         fields = (
#             'user',
#             'data_nascimento', 'nrBI', 'telefone', 'endereco',
#             'salario', 'ativo',
#         )

#     def validate(self, data):
#         if not self.instance and not data.get('user'):
#             raise serializers.ValidationError({'user': 'Os dados do utilizador são obrigatórios.'})
#         return data

#     @transaction.atomic
#     def create(self, validated_data):
#         user_data = validated_data.pop('user')
#         user = _criar_user_de_validated(user_data, User.Cargo.MONITOR)
#         return Monitor.objects.create(user=user, **validated_data)

#     @transaction.atomic
#     def update(self, instance, validated_data):
#         user_data = validated_data.pop('user', {})
#         if user_data:
#             UserUpdateSerializer(instance.user, data=user_data, partial=True).save()
#         for attr, val in validated_data.items():
#             setattr(instance, attr, val)
#         instance.save()
#         return instance


# class MonitorListSerializer(serializers.ModelSerializer):
#     nome = serializers.CharField(source='user.nome', read_only=True)
#     tem_rota_ativa = serializers.BooleanField(read_only=True)

#     class Meta:
#         model = Monitor
#         fields = ('id', 'nome', 'salario', 'tem_rota_ativa', 'ativo')
