"""modelo de base de dados"""

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.core.validators import EmailValidator
from django.contrib.auth.models import (AbstractBaseUser,
                                        BaseUserManager,
                                        Group,
                                        Permission)

validar_email = EmailValidator(message="O campo de email deve conter um endereço de email válido.")

class UserManager(BaseUserManager):
    """Manager users"""
    def create_user(self, email, nome, password=None, **extra_fields):
        """cria, salva, e retorna um novo user"""
        if not email:
            raise ValueError("O campo de email é obrigatório.")
        if not nome:
            raise ValueError("O campo de nome é obrigatório.")
        if password and len(password) < 8:
            raise ValueError("A senha deve conter pelo menos 8 caracteres.")

        email = self.normalize_email(email).lower().strip()
        nome = nome.strip().title()

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nome, password, **extra_fields):
        """criar e retorna um novo super usuario"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(email, nome, role=User.cargo.ADMIN, password=password, **extra_fields)


class User(AbstractBaseUser):

    class Cargo(models.TextChoices):
        DMIN = "ADMIN", "Administrador"
        ALUNO = "ALUNO", "Aluno"
        ENCARREGADO = "ENCARREGADO", "Encarregado"
        MOTORISTA = "MOTORISTA", "Motorista"

    username = None
    email = models.EmailField(unique=True)
    nome = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Cargo.choices, default=Cargo.ADMIN)

    salario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=Decimal("0.00"), help_text="Salário do usuário (se vazio, aplica valor padrão).")
    data_criacao = models.DateTimeField(default=timezone.now, editable=False)
    data_atualizacao = models.DateTimeField(auto_now=True, editable=False)

    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_groups",
        blank=True, help_text="Os grupos aos quais este usuário pertence."
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions",
        blank=True,
        help_text="Permissões específicas para este usuário."
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ["nome"]

    def save(self, *args, **kwargs):
        if self.nome:
            self.nome = self.nome.strip().title()
        if self.email:
            self.email = self.email.strip().lower()
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} - {self.email} ({self.get_role_display()})"
