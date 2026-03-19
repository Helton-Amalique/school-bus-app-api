"""
core/models.py
Sistema de Transporte Escolar — Modelos base
"""


from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    Group,
    Permission,
    PermissionsMixin,
)
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


validar_email = EmailValidator(
    message="O campo de email deve conter um endereço de email válido."
)

validador_bi = RegexValidator(
    regex=r'^\d{12}[A-Z]{1}$',
    message="Formato inválido para BI. Use 12 dígitos seguidos de 1 letra maiúscula."
)

validador_carta = RegexValidator(
    regex=r'^\d{9}$',
    message="Formato inválido para carta de condução. Use 9 dígitos."
)


class UserManager(BaseUserManager):
    """Manager de utilizadores customizado."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("O campo de email é obrigatório.")
        if not extra_fields.get('nome'):
            raise ValueError("O campo de nome é obrigatório.")
        if not extra_fields.get('role'):
            raise ValueError("O campo de role é obrigatório.")
        if password and len(password) < 8:
            raise ValueError("A senha deve conter pelo menos 8 caracteres.")

        email = self.normalize_email(email).lower().strip()
        extra_fields['nome'] = extra_fields['nome'].strip().title()

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('nome', 'Administrador')
        extra_fields.setdefault('role', 'ADMIN')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superutilizador deve ter is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superutilizador deve ter is_superuser=True.")

        return self.create_user(email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Utilizador base do sistema.

    O campo `role` define o tipo de perfil.
    Cada role corresponde a exactamente um perfil de detalhe
    (Aluno, Motorista, Monitor, Gestor, Encarregado) ligado via OneToOne.
    """

    class Cargo(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        GESTOR = "GESTOR", "Gestor"
        MOTORISTA = "MOTORISTA", "Motorista"
        MONITOR = "MONITOR", "Monitor"
        ENCARREGADO = "ENCARREGADO", "Encarregado"
        ALUNO = "ALUNO", "Aluno"

    username = None

    email = models.EmailField(
        unique=True,
        validators=[validar_email],
        error_messages={'unique': "Este email já está em uso."}
    )
    nome = models.CharField(max_length=255)
    role = models.CharField(
        max_length=20,
        choices=Cargo.choices,
        default=Cargo.ADMIN,
        db_index=True,
    )
    data_criacao = models.DateTimeField(default=timezone.now, editable=False)
    data_atualizacao = models.DateTimeField(auto_now=True, editable=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_groups",
        blank=True,
        help_text="Os grupos aos quais este utilizador pertence."
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions",
        blank=True,
        help_text="Permissões específicas para este utilizador."
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome', 'role']

    class Meta:
        verbose_name = "Utilizador"
        verbose_name_plural = "Utilizadores"
        indexes = [
            models.Index(fields=['role', 'is_active'], name='idx_user_role_active'),
        ]

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()
        if self.nome:
            self.nome = self.nome.strip().title()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def nome_curto(self) -> str:
        """Primeiro nome — útil para notificações e emails."""
        return self.nome.split()[0] if self.nome else ''

    def __str__(self):
        return f"{self.nome} ({self.get_role_display()})"


class PerfilMixin(models.Model):
    """
    Campos e comportamentos comuns a Encarregado, Aluno,
    Motorista, Gestor e Monitor.

    Evita duplicação de: data_nascimento, BI, telefone, endereço,
    ativo, timestamps e a validação de nascimento.
    """

    data_nascimento = models.DateField()
    nrBI = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        validators=[validador_bi],
        help_text="Número de bilhete de identidade"
    )
    telefone = PhoneNumberField(region="MZ", unique=True, null=True, blank=True)
    endereco = models.CharField(max_length=255, null=True, blank=True)
    ativo = models.BooleanField(default=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @property
    def idade(self) -> int:
        if not self.data_nascimento:
            return 0
        hoje = date.today()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
        )

    def _validar_nascimento(self):
        """Reutilizável por todos os clean() dos perfis."""
        if self.data_nascimento and self.data_nascimento > date.today():
            raise ValidationError(
                {"data_nascimento": "A data de nascimento não pode ser no futuro."}
            )

    def save(self, *args, **kwargs):
        if self.endereco:
            self.endereco = self.endereco.strip()
        self.full_clean()
        super().save(*args, **kwargs)


class Encarregado(PerfilMixin):
    """Encarregado de educação — responsável por um ou mais alunos."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'ENCARREGADO'},
        related_name='perfil_encarregado',
    )

    class Meta:
        verbose_name = "Encarregado"
        verbose_name_plural = "Encarregados"

    def clean(self):
        self._validar_nascimento()
        if self.user_id and self.user.role != User.Cargo.ENCARREGADO:
            raise ValidationError({"user": "O utilizador deve ter o role ENCARREGADO."})

    def __str__(self):
        return f"Encarregado: {self.user.nome}"


class Aluno(PerfilMixin):
    """
    Aluno do sistema de transporte escolar.

    NOTA: a lógica de bloqueio por mensalidades em atraso vive em
    financeiro.Mensalidade para evitar dependência circular de core → financeiro.
    Para verificar acesso, usar:
        financeiro.models.Mensalidade.objects.aluno_tem_acesso_bloqueado(aluno)
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'ALUNO'},
        related_name='perfil_aluno',
    )
    encarregado = models.ForeignKey(
        Encarregado,
        on_delete=models.CASCADE,
        related_name='alunos',
    )
    escola_dest = models.CharField(max_length=255, db_index=True)
    classe = models.CharField(max_length=25)
    mensalidade = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.0'))],
        default=Decimal('0.00'),
        help_text="Valor base da mensalidade do aluno"
    )

    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"

    def clean(self):
        self._validar_nascimento()
        if self.data_nascimento and self.idade < 3:
            raise ValidationError(
                {"data_nascimento": "O aluno deve ter pelo menos 3 anos de idade."}
            )
        if self.user_id and self.user.role != User.Cargo.ALUNO:
            raise ValidationError({"user": "O utilizador deve ter o role ALUNO."})

    def __str__(self):
        return f"Aluno: {self.user.nome}"


class Motorista(PerfilMixin):
    """
    Motorista responsável pela condução do veículo.

    related_name='perfil_motorista' → acesso via user.perfil_motorista
    consistente com TransporteAlunoViewSet e financeiro.Funcionario.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'MOTORISTA'},
        related_name='perfil_motorista',   # ← CORRIGIDO (era 'motorista')
    )
    carta_conducao = models.CharField(
        max_length=20,
        unique=True,
        validators=[validador_carta],
    )
    validade_da_carta = models.DateField(null=True, blank=False)
    salario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.0'))],
        default=Decimal('0.00'),
    )

    class Meta:
        verbose_name = "Motorista"
        verbose_name_plural = "Motoristas"

    def carta_conducao_vencida(self) -> bool:
        if not self.validade_da_carta:
            return True
        return self.validade_da_carta < date.today()

    def clean(self):
        self._validar_nascimento()
        if self.data_nascimento and self.idade < 18:
            raise ValidationError(
                {"data_nascimento": "O motorista deve ter pelo menos 18 anos."}
            )
        if self.validade_da_carta and self.validade_da_carta < date.today():
            raise ValidationError(
                {"validade_da_carta": "A carta de condução está expirada."}
            )
        if self.salario is not None and self.salario < Decimal('0'):
            raise ValidationError({"salario": "O salário não pode ser negativo."})
        if self.user_id and self.user.role != User.Cargo.MOTORISTA:
            raise ValidationError({"user": "O utilizador deve ter o role MOTORISTA."})

    def __str__(self):
        return f"Motorista: {self.user.nome}"


class Gestor(PerfilMixin):
    """
    Gestor operacional.
    Gere alunos, encarregados, veículos, rotas e motoristas.
    Aprova manutenções e abastecimentos conforme o departamento.
    """

    class Departamento(models.TextChoices):
        FROTA = 'FROTA', 'Gestão de Frota'
        ACADEMICO = 'ACADEMICO', 'Gestão Académica'
        FINANCEIRO = 'FINANCEIRO', 'Financeiro'
        GERAL = 'GERAL', 'Geral'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'GESTOR'},
        related_name='perfil_gestor',
    )
    departamento = models.CharField(
        max_length=20,
        choices=Departamento.choices,
        default=Departamento.GERAL,
        db_index=True,
        help_text="Área de responsabilidade do gestor"
    )
    salario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.0'))],
        default=Decimal('0.00'),
    )
    motoristas_supervisionados = models.ManyToManyField(
        Motorista,
        blank=True,
        related_name='gestores',
        help_text="Motoristas sob supervisão deste gestor"
    )

    class Meta:
        verbose_name = "Gestor"
        verbose_name_plural = "Gestores"

    def pode_aprovar_manutencao(self) -> bool:
        return self.departamento in (
            Gestor.Departamento.FROTA, Gestor.Departamento.GERAL
        ) and self.ativo

    def pode_aprovar_abastecimento(self) -> bool:
        return self.departamento in (
            Gestor.Departamento.FROTA, Gestor.Departamento.GERAL
        ) and self.ativo

    def clean(self):
        self._validar_nascimento()
        if self.data_nascimento and self.idade < 18:
            raise ValidationError(
                {"data_nascimento": "O gestor deve ter pelo menos 18 anos."}
            )
        if self.user_id and self.user.role != User.Cargo.GESTOR:
            raise ValidationError({"user": "O utilizador deve ter o role GESTOR."})

    def __str__(self):
        return f"Gestor: {self.user.nome} ({self.get_departamento_display()})"


class Monitor(PerfilMixin):
    """
    Monitor — acompanha os alunos dentro da carrinha.
    Responsável pelo check-in/check-out durante a viagem.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'MONITOR'},
        related_name='perfil_monitor',   # ← CORRIGIDO (era 'monitor')
    )
    salario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.0'))],
        default=Decimal('0.00'),
    )

    class Meta:
        verbose_name = "Monitor"
        verbose_name_plural = "Monitores"

    @property
    def rota_ativa(self):
        """Devolve a rota ativa actual do monitor, se existir."""
        return self.rotas.filter(ativo=True).first()

    def tem_rota_ativa(self) -> bool:
        return self.rotas.filter(ativo=True).exists()

    def clean(self):
        self._validar_nascimento()
        if self.data_nascimento and self.idade < 18:
            raise ValidationError(
                {"data_nascimento": "O monitor deve ter pelo menos 18 anos."}
            )
        if self.user_id and self.user.role != User.Cargo.MONITOR:
            raise ValidationError({"user": "O utilizador deve ter o role MONITOR."})

    def __str__(self):
        return f"Monitor: {self.user.nome}"
