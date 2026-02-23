"""modelo de base de dados"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MinLengthValidator, RegexValidator
from decimal import Decimal
from datetime import date
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import (AbstractBaseUser,
                                        BaseUserManager,
                                        PermissionsMixin)

validador_carta = RegexValidator(
    regex=r'^\d{9}$',
    message="Formato inválido para carta de condução. Use 9 dígitos."
)

class Encarregado(models.Model):
    """Encarregado de educação"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'ENCARREGADO'},
        related_name='encarregado'
    )
    nrBI = models.CharField(max_length=30, unique=True, db_index=True, validators=[RegexValidator(r'^\d{12}[A-Z]{1}$', "Formato inválido para BI")], help_text="Número de bilhete de identidade")
    telefone = PhoneNumberField(region="MZ", unique=True, null=True, blank=True)
    endereco = models.CharField(max_length=255, null=True, blank=True)
    ativo = models.BooleanField(default=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Encarregado: {self.user.nome} - {self.user.email}"


class Aluno(models.Model):
    """Aluno do sistema"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'ALUNO'},
        related_name='aluno'
    )
    encarregado = models.ForeignKey(Encarregado, on_delete=models.CASCADE, related_name='alunos')
    data_nascimento = models.DateField()
    nrBI = models.CharField(max_length=30, unique=True, db_index=True, validators=[RegexValidator(r'^\d{12}[A-Z]{1}$', "Formato inválido para BI")])
    escola_dest = models.CharField(max_length=255, db_index=True)
    classe = models.CharField(max_length=25)
    mensalidade = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.0'))], default=Decimal('0.00'))
    ativo = models.BooleanField(default=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def clean(self):
        hoje = date.today()
        if self.data_nascimento > hoje:
            raise ValidationError("A data de nascimento não pode ser no futuro.")
        ideda = self.idade
        if ideda < 3:
            raise ValidationError("O aluno deve ter pelo menos 3 anos de idade.")

    @property
    def idade(self):
        hoje = date.today()
        idade = hoje.year - self.data_nascimento.year
        if (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day):
            idade -= 1
        return idade

    def __str__(self):
        return f"Aluno: {self.user.nome} - {self.user.email}"


class Motorista(models.Model):
    """Motorista do sistema"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'MOTORISTA'},
        related_name='motorista'
    )
    data_nascimento = models.DateField()
    nrBI = models.CharField(max_length=30, unique=True, db_index=True, validators=[RegexValidator(r'^\d{12}[A-Z]{1}$', "Formato inválido para BI")])
    telefone = PhoneNumberField(region="MZ", unique=True, null=True, blank=True)
    endereco = models.CharField(max_length=255, null=True, blank=True)
    carta_conducao = models.CharField(
        max_length=20, unique=True,
        validators=[validador_carta]
    )
    validade_da_carta = models.DateField(null=True, blank=False)
    salario = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.0'))], default=Decimal('0.00'))
    ativo = models.BooleanField(default=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    @property
    def idade(self)->int:
        """Calcula a idade baseada na data de nascimento"""
        if not self.data_nascimento:
            return 0
        hoje = date.today()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
        )

    def clean(self):
        hoje = date.today()
        if self.data_nascimento > hoje:
            raise ValidationError("A data de nascimento não pode ser no futuro.")
        if self.idade < 18:
            raise ValidationError("O motorista deve ter pelo menos 18 anos.")
        if self.validade_da_carta and self.validade_da_carta < hoje:
            raise ValidationError("A carta de condução está expirada.")
        if self.salario < 0:
            raise ValidationError("O salario nao pode ser negativo.")
        if self.user.role != "MOTORISTA" and self.salario and self.salario > 0:
            raise ValidationError("Somente motoristas podem ter salário definido.")

    def __str__(self):
        return f"Motorista: {self.user.nome} - {self.user.email}"

    def save(self, *args, **kwargs):
        if self.endereco:
            self.endereco = self.endereco.strip()
        self.full_clean()
        super().save(*args, **kwargs)
