import datetime
from django.db import models
from core.models import Aluno, Motorista
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator

validar_matric = RegexValidator(
    regex=r'^[A-Z]{3}-\d{3}-[A-Z]{2}$',
    message='Placa inválida. Ex: ABC-123-XY'
)

class VeiculoManager(models.Manager):
    def ativos(self):
        return self.filter(ativo=True)


class Veiculo(models.Model):
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    matricula = models.CharField(max_length=12, unique=True, validators=[validar_matric], db_index=True, help_text='Matricula do veiculo')
    capacidade = models.PositiveIntegerField(validators=[MinValueValidator(1)], help_text='Numero maximo de passageiros')
    motorista = models.ForeignKey(Motorista, on_delete=models.PROTECT, null=True, blank=True, related_name='veiculos')
    ativo = models.BooleanField(default=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = VeiculoManager()

    class Meta:
        verbose_name = "Veiculo"
        verbose_name_plural = "Veiculos"
        ordering = ["matricula"]

    def save(self, *args, **kwargs):
        self.marca = self.marca.strip().title()
        self.modelo = self.modelo.strip().title()
        self.matricula = self.matricula.strip().upper()
        super().save(*args, **kwargs)

    @property
    def vagas_disponiveis(self) -> int:
        rota_ativa = self.rotas.filter(ativo=True).first()
        if not rota_ativa:
            return self.capacidade
        alunos_na_rota = rota_ativa.alunos.count()
        return max(self.capacidade - alunos_na_rota, 0)

    def __str__(self):
        return f"{self.modelo} - {self.matricula}"


class Rota(models.Model):
    nome = models.CharField(max_length=255, db_index=True)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="rotas")
    hora_partida = models.TimeField(default=datetime.time(5, 20))
    hora_chegada = models.TimeField(default=datetime.time(7, 0))
    descricao = models.TextField(blank=True, null=True)
    alunos = models.ManyToManyField(Aluno, related_name="rotas_transporte")
    ativo = models.BooleanField(default=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rota"
        verbose_name_plural = "Rotas"
        ordering = ["nome"]

    def clean(self):
        if not hasattr(self, "veiculo"):
            return

        if self.veiculo and not self.veiculo.motorista:
            raise ValidationError({"veiculo": "O veiculo selecionado nao te motorista atribuido"})
        if self.veiculo and not self.veiculo.ativo:
            raise ValidationError({"veiculo": "O veiculo selecionado esta inativo."})
        if self.hora_chegada <= self.hora_partida:
            raise ValidationError({"hora_chegada": "A hora de chagada deve ser posterior a hora de partida"})
        if self.veiculo and self.alunos.count() > self.veiculo.capacidade:
            raise ValidationError({"alunos": "Numero de alunos excede a capacidade do veiculo"})
        # if self.veiculo and self.veiculo.rotas.filter(ativo=True).exclude(pk=self.pk).exists():
        #     raise ValidationError({"veiculo": "Este veiculo ja possui um rota ativa"})

        rota_confilito = Rota.objects.filter(veiculo=self.veiculo, ativo=True).exclude(pk=self.pk)
        if rota_confilito.exists():
            raise ValidationError({"veiculo": "Este veiculo ja possui uma rota ativa"})

    @property
    def motorista(self):
        return self.veiculo.motorista

    def __str__(self):
        return f"Rota: {self.nome} - Veiculo: {self.veiculo.matricula}"


class TransporteAluno(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    rota = models.ForeignKey(Rota, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[("PENDENTE", "Pendente"), ("EMBARCADO", "Embarcado"), ("DESEMBARCADO", "Desembarcado"), ], default="PENDENTE")
    data = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Transporte de Aluno"
        verbose_name_plural = "Transportes de Alunos"
        ordering = ["-data"]

    def __str__(self):
        return f"{self.aluno} - {self.rota} ({self.status})"
