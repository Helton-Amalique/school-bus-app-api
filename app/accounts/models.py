"""modelo de base de dados — User customizado"""

from django.db import models
from django.utils import timezone
from django.core.validators import EmailValidator
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
    Group,
    Permission,
)

validar_email = EmailValidator(
    message="O campo de email deve conter um endereço de email válido."
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
        extra_fields.setdefault('role', User.Cargo.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superutilizador deve ter is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superutilizador deve ter is_superuser=True.")
        return self.create_user(email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    class Cargo(models.TextChoices):
        ADMIN       = "ADMIN",       "Administrador"
        ALUNO       = "ALUNO",       "Aluno"
        ENCARREGADO = "ENCARREGADO", "Encarregado"
        GESTOR      = "GESTOR",      "Gestor"
        MOTORISTA   = "MOTORISTA",   "Motorista"
        MONITOR     = "MONITOR",     "Monitor"

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
    REQUIRED_FIELDS = ["nome", "role"]

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
        return f"{self.nome} - {self.email} ({self.get_role_display()})"
