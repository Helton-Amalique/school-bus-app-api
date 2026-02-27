import datetime
from django.db import models
from django.db.models import Count, Q, F
from core.models import Aluno, Motorista
# from core.transporte import rota
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator

validar_matric = RegexValidator(
    regex=r'^[A-Z]{3}-\d{3}-[A-Z]{2}$',
    message='Placa inválida. Ex: ABC-123-XY'
)

class VeiculoManager(models.Manager):
    def ativos(self):
        return self.filter(ativo=True)

    def com_vagas(self):
        return self.annotate(alunos_count=Count('rotas__alunos', filter=Q(rotas__ativo=True)))


class Veiculo(models.Model):
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    matricula = models.CharField(max_length=12, unique=True, validators=[validar_matric], db_index=True, error_messages={'unique': 'A matrícula do veículo já está em uso.'})
    capacidade = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(50, message="A capacidade do veículo deve ser menor ou igual a 50.")],
        help_text='Número máximo de passageiros'
    )

    motorista = models.ForeignKey(Motorista, on_delete=models.PROTECT, null=True, blank=True, related_name='veiculos')
    ativo = models.BooleanField(default=True, db_index=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    quilometragem_atual = models.PositiveIntegerField(default=0, help_text='Quilometragem atual do veiculo')
    data_ultima_revisao = models.DateField(null=True, blank=True, help_text='Data da ultima revisao')
    km_proxima_revisao = models.PositiveIntegerField(default=10000, help_text='Quilometragem para a proxima revisao')

    objects = VeiculoManager()

    class Meta:
        verbose_name = "Veiculo"
        verbose_name_plural = "Veiculos"
        ordering = ["matricula"]

    def clean(self):
        super().clean()

        if not self.motorista:
            raise ValidationError({'motorista': 'O veículo deve ter um motorista atribuído.'})

        if self.motorista and self.ativo:
            outros_veiculos = Veiculo.objects.filter(
                motorista=self.motorista,
                ativo=True
            ).exclude(pk=self.pk)

            if outros_veiculos.exists():
                raise ValidationError({
                    'motorista': f'O motorista {self.motorista} já está alocado ao veículo {outros_veiculos.first().matricula}.'
                })

    def save(self, *args, **kwargs):
        self.marca = self.marca.strip().title()
        self.modelo = self.modelo.strip().title()
        self.matricula = self.matricula.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def vagas_disponiveis(self) -> int:
        rota_ativa = self.rotas.filter(ativo=True).first()
        if not rota_ativa:
            return self.capacidade
        alunos_na_rota = rota_ativa.alunos.count()
        return self.capacidade - alunos_na_rota

    def em_manutencao(self):
        return self.manutencoes.filter(concluida=False).exists()

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
        super().clean()
        if not self.veiculo_id:
            raise ValidationError({"veiculo": "É obrigatório selecionar um veículo para a rota."})
        if not self.veiculo.motorista:
            raise ValidationError({"veiculo": "O veículo selecionado não tem motorista atribuído."})
        if not self.veiculo.ativo:
            raise ValidationError({"veiculo": "O veículo selecionado está inativo."})
        if self.hora_chegada <= self.hora_partida:
            raise ValidationError({"hora_chegada": "A hora de chegada deve ser posterior à hora de partida."})
        if self.veiculo.manutencoes.filter(concluida=False).exists():
            raise ValidationError({"veiculo": "Este veículo está em manutenção."})
        if self.veiculo.capacidade > 50:
            raise ValidationError({"veiculo": "A capacidade do veículo deve ser no máximo 50 passageiros."})
        if self.ativo:
            rota_conflito = Rota.objects.filter(veiculo=self.veiculo, ativo=True).exclude(pk=self.pk)
            if rota_conflito.exists():
                raise ValidationError({"veiculo": "Este veículo já possui uma rota ativa."})

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
        constraints = [
            models.UniqueConstraint(fields=['aluno', 'rota'], name='unique_transporte_aluno_diario')
        ]

    def clean(self):
        super().clean()
        if not self.rota.ativo:
            raise ValidationError({"rota": "A rota selecionada esta inativa."})
        if self.rota.veiculo.em_manutencao():
            raise ValidationError({"rota": "O veiculo da rota selecionada esta em manutencao."})

    def __str__(self):
        return f"{self.aluno} - {self.rota} ({self.status})"


class Manutencao(models.Model):
    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE, related_name="manutencoes")
    descricao = models.TextField()
    data_inicio = models.DateField()
    quilometragem_no_momento_revisao = models.PositiveIntegerField(default=0)
    data_fim = models.DateField(null=True, blank=True)
    custo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    concluida = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Manutenção"
        verbose_name_plural = "Manutenções"
        ordering = ["-data_inicio"]

    def clean(self):
        if self.data_fim and self.data_inicio and self.data_fim < self.data_inicio:
            raise ValidationError({"data_fim": "A data de fim deve ser posterior a data de início."})

    data_ultima_revisao = models.DateField(null=True, blank=True)
    km_proxima_revisao = models.PositiveIntegerField(default=7000)

    def concluir_manutencao(self, km_proximo_ajuste=7000):
        self.concluida = True
        self.data_fim = datetime.date.today()

        self.veiculo.data_ultima_revisao = self.data_fim
        if self.quilometragem_no_momento_revisao > self.veiculo.quilometragem_atual:
            self.veiculo.quilometragem_atual = self.quilometragem_no_momento_revisao

        self.veiculo.km_proxima_revisao = self.veiculo.quilometragem_atual + km_proximo_ajuste
        self.veiculo.save()
        self.save()

    # def clean(self):
    #     super().clean()
    #     if self.data_fim and self.data_inicio and self.data_fim < self.data_inicio:
    #         raise ValidationError({"data_fim": "A data de fim deve ser posterior a data de início."})
    #     if self.quilometragem_no_momento_revisao < self.veiculo.quilometragem_atual:
    #         raise ValidationError({"quilometragem_no_momento_revisao": f"A quilometragem no momento da revisão não pode ser menor que a quilometragem atual do veículo ({self.veiculo.quilometragem_atual})."})

    def __str__(self):
        return f"{self.veiculo.matricula} - {self.descricao[:30]}"
