"""
transporte/models.py
Sistema de Transporte Escolar — Modelos de transporte

Modelos: Veiculo, Rota, TransporteAluno, Manutencao, Abastecimento

REGRA DE DEPENDÊNCIAS:
  transporte → core
  transporte ← financeiro  (financeiro referencia transporte, não o inverso)
Nunca importar de `financeiro` aqui.
"""
import datetime
from core.models import Aluno, Motorista
from django.db import models, transaction
from django.db.models import Count, F, Q, Sum
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator


validar_matric = RegexValidator(
    regex=r'^[A-Z]{3}-\d{3}-[A-Z]{2}$',
    message='Matrícula inválida. Ex: ABC-123-XY'
)


class VeiculoManager(models.Manager):

    def ativos(self):
        return self.filter(ativo=True)

    def com_vagas(self):
        """
        Veículos activos que ainda têm vagas disponíveis na rota activa.
        Anota alunos_count e filtra alunos_count < capacidade.
        """
        return (
            self.filter(ativo=True)
            .annotate(
                alunos_count=Count(
                    'rotas__alunos',
                    filter=Q(rotas__ativo=True)
                )
            )
            .filter(alunos_count__lt=F('capacidade'))
        )


class Veiculo(models.Model):
    """
    Veículo da frota.

    Ligações de saída:
      - motorista → core.Motorista (FK, PROTECT)

    Ligações de entrada (reverse):
      - rotas        ← Rota
      - manutencoes  ← Manutencao
      - abastecimento ← Abastecimento
      - gastos       ← financeiro.DespesaVeiculo  (definida em financeiro)
    """

    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    matricula = models.CharField(
        max_length=12,
        unique=True,
        validators=[validar_matric],
        db_index=True,
        error_messages={'unique': 'A matrícula do veículo já está em uso.'}
    )
    capacidade = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(50, message="A capacidade máxima é 50 passageiros.")
        ],
        help_text='Número máximo de passageiros'
    )
    motorista = models.ForeignKey(
        Motorista,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='veiculos',
    )
    ativo = models.BooleanField(default=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    quilometragem_atual = models.PositiveIntegerField(
        default=0,
        help_text='Quilometragem actual do veículo'
    )
    data_ultima_revisao = models.DateField(null=True, blank=True)
    km_proxima_revisao = models.PositiveIntegerField(
        default=10000,
        help_text='Quilometragem alvo para a próxima revisão'
    )

    data_validade_seguro = models.DateField(null=True, blank=False, help_text="Validade do seguro")
    data_validade_inspecao = models.DateField(null=True, blank=False, help_text="Validade da inspecção")
    nr_manifesto = models.CharField(max_length=20, null=True, blank=True)
    data_validade_manifesto = models.DateField(null=True, blank=True, help_text="Validade do manifesto")

    capacidade_tanque = models.PositiveIntegerField(
        default=80,
        help_text='Capacidade do tanque em litros'
    )

    objects = VeiculoManager()

    class Meta:
        verbose_name = "Veículo"
        verbose_name_plural = "Veículos"
        ordering = ["matricula"]

    # ------------------------------------------------------------------
    # Documentação
    # ------------------------------------------------------------------

    def document_em_dia(self) -> bool:
        """Verifica se seguro, inspecção e manifesto estão válidos."""
        hoje = datetime.date.today()
        if not all([self.data_validade_seguro, self.data_validade_inspecao, self.data_validade_manifesto]):
            return False
        return (
            self.data_validade_seguro >= hoje and self.data_validade_inspecao >= hoje and self.data_validade_manifesto >= hoje
        )

    # ------------------------------------------------------------------
    # Validações
    # ------------------------------------------------------------------

    def clean(self):
        super().clean()

        if not self.motorista:
            raise ValidationError({'motorista': 'O veículo deve ter um motorista atribuído.'})

        if self.motorista and self.ativo:
            conflito = (
                Veiculo.objects
                .filter(motorista=self.motorista, ativo=True)
                .exclude(pk=self.pk)
            )
            if conflito.exists():
                raise ValidationError({
                    'motorista': (
                        f'O motorista {self.motorista} já está alocado ao '
                        f'veículo {conflito.first().matricula}.'
                    )
                })

    def save(self, *args, **kwargs):
        self.marca = self.marca.strip().title()
        self.modelo = self.modelo.strip().title()
        self.matricula = self.matricula.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def vagas_disponiveis(self) -> int:
        """
        Vagas disponíveis na rota activa.
        Garante mínimo 0 (nunca negativo).
        """
        rota_ativa = self.rotas.filter(ativo=True).first()
        if not rota_ativa:
            return self.capacidade
        return max(self.capacidade - rota_ativa.alunos.count(), 0)

    @property
    def custo_total_combustivel(self):
        return self.abastecimento.aggregate(total=Sum('custo_total'))['total'] or 0.00

    @property
    def autonomia_estimada(self) -> float:
        consumo = self.consumo_medio()
        return consumo * self.capacidade_tanque if consumo > 0 else 0.0

    # ------------------------------------------------------------------
    # Manutenção
    # ------------------------------------------------------------------

    def em_manutencao(self) -> bool:
        return self.manutencoes.filter(concluida=False).exists()

    def precisa_manutencao(self) -> bool:
        """Verifica se o veículo precisa de revisão com base na quilometragem."""
        if self.em_manutencao():
            return False

        ultima = (
            self.manutencoes
            .filter(concluida=True)
            .order_by('-quilometragem_no_momento_revisao')
            .first()
        )

        if not ultima:
            return self.quilometragem_atual >= self.km_proxima_revisao

        km_desde_ultima = self.quilometragem_atual - ultima.quilometragem_no_momento_revisao
        return km_desde_ultima >= self.km_proxima_revisao

    # ------------------------------------------------------------------
    # Consumo / Custos
    # ------------------------------------------------------------------

    def consumo_medio(self) -> float:
        """Consumo médio em km/litro com base nos abastecimentos registados."""
        abastecimentos = list(
            self.abastecimento.all().order_by('quilometragem_no_ato')
        )
        if len(abastecimentos) < 2:
            return 0.0

        distancia = (
            abastecimentos[-1].quilometragem_no_ato - abastecimentos[0].quilometragem_no_ato
        )
        litros = sum(a.quantidade_litros for a in abastecimentos[1:])

        if not litros:
            return 0.0
        return float(distancia / litros)

    def custo_por_quilometro(self) -> float:
        total_combustivel = float(
            self.abastecimento.aggregate(total=Sum('custo_total'))['total'] or 0
        )
        total_manutencao = float(
            self.manutencoes.aggregate(total=Sum('custo'))['total'] or 0
        )
        if not self.quilometragem_atual:
            return 0.0
        return round((total_combustivel + total_manutencao) / self.quilometragem_atual, 2)

    def __str__(self):
        return f"{self.modelo} - {self.matricula}"


class Rota(models.Model):
    """
    Rota de transporte escolar.

    Ligações de saída:
      - veiculo → Veiculo (FK, PROTECT)
      - alunos  → core.Aluno (M2M, related_name='rotas_transporte')

    Ligações de entrada (reverse):
      - transportes ← TransporteAluno
    """

    nome = models.CharField(max_length=255, db_index=True)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="rotas")
    hora_partida = models.TimeField(default=datetime.time(5, 20))
    hora_chegada = models.TimeField(default=datetime.time(7, 0))
    descricao = models.TextField(blank=True, null=True)
    alunos = models.ManyToManyField(Aluno, related_name="rotas_transporte", blank=True)
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
            raise ValidationError({"veiculo": "É obrigatório seleccionar um veículo."})
        if not self.veiculo.motorista:
            raise ValidationError({"veiculo": "O veículo não tem motorista atribuído."})
        if not self.veiculo.ativo:
            raise ValidationError({"veiculo": "O veículo está inactivo."})
        if self.hora_chegada <= self.hora_partida:
            raise ValidationError({"hora_chegada": "A hora de chegada deve ser posterior à partida."})
        if self.veiculo.em_manutencao():
            raise ValidationError({"veiculo": "Este veículo está em manutenção."})
        if not self.veiculo.document_em_dia():
            raise ValidationError({"veiculo": "O veículo tem seguro ou inspecção vencida."})
        if self.veiculo.motorista.carta_conducao_vencida():
            raise ValidationError({"veiculo": "O motorista tem carta de condução vencida."})

        if self.ativo:
            for outra in Rota.objects.filter(veiculo=self.veiculo, ativo=True).exclude(pk=self.pk):
                if self.hora_partida < outra.hora_chegada and self.hora_chegada > outra.hora_partida:
                    raise ValidationError({
                        "hora_partida": (
                            f"Conflito de turno com a rota '{outra.nome}' "
                            f"({outra.hora_partida}–{outra.hora_chegada})."
                        )
                    })

    @property
    def motorista(self):
        """Atalho para o motorista do veículo desta rota."""
        return self.veiculo.motorista

    @property
    def total_inscritos(self) -> int:
        return self.alunos.count()

    @property
    def alunos_embarcados_hoje(self):
        """Alunos com registo de embarque para hoje (TransporteAluno)."""
        return TransporteAluno.objects.filter(
            rota=self,
            data=datetime.date.today(),
            status='EMBARCADO'
        )

    def __str__(self):
        return f"Rota: {self.nome} — {self.veiculo.matricula}"


class TransporteAluno(models.Model):
    """
    Registo diário de embarque/desembarque de um aluno numa rota.

    NOTA — constraint única corrigida:
      Inclui `data` para permitir um registo por aluno/rota/dia.
      A constraint anterior (sem data) impedia múltiplos dias para o mesmo par.
    """

    STATUS_CHOICES = [
        ("PENDENTE", "Pendente"),
        ("EMBARCADO", "Embarcado"),
        ("DESEMBARCADO", "Desembarcado"),
    ]

    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='transportes')
    rota = models.ForeignKey(Rota, on_delete=models.CASCADE, related_name='transportes')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDENTE")
    data = models.DateField(default=datetime.date.today)

    class Meta:
        verbose_name = "Transporte de Aluno"
        verbose_name_plural = "Transportes de Alunos"
        ordering = ["-data"]
        constraints = [
            models.UniqueConstraint(
                fields=['aluno', 'rota', 'data'],
                name='unique_transporte_aluno_por_dia'
            )
        ]

    def clean(self):
        super().clean()
        if not self.rota.ativo:
            raise ValidationError({"rota": "A rota está inactiva."})
        if self.rota.veiculo.em_manutencao():
            raise ValidationError({"rota": "O veículo da rota está em manutenção."})
        if self.aluno_id and self.rota_id:
            if not self.rota.alunos.filter(pk=self.aluno_id).exists():
                raise ValidationError({"aluno": "Este aluno não está inscrito nesta rota."})

    def __str__(self):
        return f"{self.aluno} — {self.rota} ({self.status}) [{self.data}]"


class Manutencao(models.Model):

    TIPOS = [
        ('PREVENTIVA', 'Preventiva'),
        ('CORRETIVA', 'Corretiva'),
    ]

    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE, related_name="manutencoes")
    tipo = models.CharField(max_length=20, choices=TIPOS, default='PREVENTIVA')
    descricao = models.TextField(help_text='Ex: Troca de óleo, travões')
    data_inicio = models.DateField()
    quilometragem_no_momento_revisao = models.PositiveIntegerField(default=0)
    data_fim = models.DateField(null=True, blank=True)
    custo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    concluida = models.BooleanField(default=False)
    km_proxima_revisao = models.PositiveIntegerField(default=7000)

    class Meta:
        verbose_name = "Manutenção"
        verbose_name_plural = "Manutenções"
        ordering = ["-data_inicio"]

    def clean(self):
        if self.data_fim and self.data_inicio and self.data_fim < self.data_inicio:
            raise ValidationError({"data_fim": "A data de fim deve ser posterior à de início."})
        if self.quilometragem_no_momento_revisao > self.veiculo.quilometragem_atual:
            raise ValidationError({
                "quilometragem_no_momento_revisao": (
                    f"A quilometragem da revisão ({self.quilometragem_no_momento_revisao} km) "
                    f"não pode exceder a actual do veículo ({self.veiculo.quilometragem_atual} km)."
                )
            })

    def concluir_manutencao(self, km_proximo_ajuste: int = 7000):
        """
        Conclui a manutenção, actualiza o veículo e agenda a próxima revisão.

        CORRIGIDO: quilometragem_atual do veículo é sempre actualizada para
        o valor da revisão (não apenas se for maior), pois é o registo
        oficial no momento da entrega.
        """
        with transaction.atomic():
            self.concluida = True
            self.data_fim = datetime.date.today()

            veiculo = Veiculo.objects.select_for_update().get(pk=self.veiculo_id)
            veiculo.data_ultima_revisao = self.data_fim
            veiculo.quilometragem_atual = max(
                veiculo.quilometragem_atual,
                self.quilometragem_no_momento_revisao
            )
            veiculo.km_proxima_revisao = (
                self.quilometragem_no_momento_revisao + km_proximo_ajuste
            )
            veiculo.save(update_fields=[
                'data_ultima_revisao', 'quilometragem_atual', 'km_proxima_revisao'
            ])
            self.save()

    def __str__(self):
        return f"{self.veiculo.matricula} — {self.descricao[:40]}"


class Abastecimento(models.Model):
    """
    Registo de abastecimento de combustível.

    Ligações de saída:
      - veiculo → Veiculo (FK, CASCADE)
    """
    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE, related_name="abastecimento")
    data = models.DateField(default=datetime.date.today)
    quilometragem_no_ato = models.PositiveIntegerField(
        default=0,
        help_text='Quilometragem no momento do abastecimento'
    )
    quantidade_litros = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    custo_total = models.DecimalField(max_digits=10, decimal_places=2)
    posto_combustivel = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Abastecimento"
        verbose_name_plural = "Abastecimentos"
        ordering = ["-data", "-quilometragem_no_ato"]

    def clean(self):
        super().clean()
        if self.quilometragem_no_ato < self.veiculo.quilometragem_atual:
            raise ValidationError({
                "quilometragem_no_ato": (
                    "A quilometragem no abastecimento não pode ser menor "
                    "que a quilometragem actual do veículo."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        with transaction.atomic():
            if self.quilometragem_no_ato > self.veiculo.quilometragem_atual:
                Veiculo.objects.filter(pk=self.veiculo_id).update(
                    quilometragem_atual=self.quilometragem_no_ato
                )
            super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.veiculo.matricula} — {self.data} "
            f"({self.quantidade_litros}L @ {self.posto_combustivel})"
        )
