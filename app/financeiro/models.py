"""
financeiro/models.py
====================
Sistema de Transporte Escolar — Módulo Financeiro

Modelos: ConfiguracaoFinanceira, Categoria, Transacao,
         Funcionario, Mensalidade, Recibo, LogNotificacoes,
         FolhaPagamento, DespesaVeiculo, DespesaGeral, BalancoMensal

REGRA DE DEPENDÊNCIAS:
  financeiro → core
  financeiro → transporte
  financeiro ← (nenhum módulo interno)

Este módulo é o "topo" da pilha — pode importar core e transporte
mas nunca é importado por eles.
"""

import calendar
import uuid
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Count, F, Sum
from django.utils import timezone


# ──────────────────────────────────────────────
# CONFIGURAÇÃO FINANCEIRA  (singleton)
# ──────────────────────────────────────────────

class ConfiguracaoFinanceira(models.Model):
    """
    Configuração global do módulo financeiro.
    Apenas um registo pode existir (singleton protegido).
    """

    dia_vencimento = models.PositiveIntegerField(
        default=5,
        help_text="Dia do mês em que a mensalidade vence"
    )
    dia_limite_pagamento = models.PositiveIntegerField(
        default=10,
        help_text="Último dia para pagamento sem multa"
    )
    valor_multa_fixa = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('500.00'),
        help_text="Valor em MT aplicado após o vencimento"
    )

    class Meta:
        verbose_name = "Configuração Financeira"
        verbose_name_plural = "Configurações Financeiras"

    def __str__(self):
        return "Configuração Geral do Sistema"

    def clean(self):
        if not (1 <= self.dia_vencimento <= 31):
            raise ValidationError({'dia_vencimento': 'O dia deve estar entre 1 e 31.'})
        if self.dia_limite_pagamento < self.dia_vencimento:
            raise ValidationError({
                'dia_limite_pagamento': 'O dia limite não pode ser anterior ao vencimento.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.pk and ConfiguracaoFinanceira.objects.exists():
            raise ValidationError('Já existe uma configuração financeira no sistema.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Impede a eliminação da configuração global."""
        pass

    @classmethod
    def get_solo(cls):
        """Obtém (ou cria) a configuração única."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def data_limite_para_mes(self, mes_referente: date) -> date:
        """Data limite de pagamento para um dado mês, respeitando o último dia."""
        ultimo_dia = calendar.monthrange(mes_referente.year, mes_referente.month)[1]
        dia_limite = min(self.dia_limite_pagamento, ultimo_dia)
        return mes_referente.replace(day=dia_limite)


# ──────────────────────────────────────────────
# CATEGORIA
# ──────────────────────────────────────────────

class Categoria(models.Model):
    TIPO_CHOICES = [('RECEITA', 'Receita'), ('DESPESA', 'Despesa')]

    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

    class Meta:
        verbose_name        = "Categoria"
        verbose_name_plural = "Categorias"
        ordering            = ['nome']
        unique_together     = ('nome', 'tipo')

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_display()})'


# ──────────────────────────────────────────────
# TRANSACAO  (ledger central)
# ──────────────────────────────────────────────

class Transacao(models.Model):
    """
    Registo financeiro central (ledger).

    Toda a entrada ou saída de dinheiro produz uma Transacao.
    Ligações de saída:
      - categoria → Categoria (FK, PROTECT)
      - aluno     → core.Aluno (FK, SET_NULL, opcional — só em receitas)
    """

    METODO_PAGAMENTO = [
        # Dinheiro e transferência bancária
        ('DINHEIRO',      'Dinheiro'),
        ('TRANSFERENCIA', 'Transferência Bancária/NIB'),
        ('CARTAO',        'Cartão de Débito/Crédito'),

        # Carteiras móveis moçambicanas
        ('MPESA',         'M-Pesa (Vodacom)'),
        ('EMOLA',         'e-Mola (Tmcel)'),
        ('MKESH',         'mKesh (Millennium BIM)'),
        ('PONTO24',       'Ponto 24 (BCI)'),
        ('MOVITEL_MONEY', 'Movitel Money'),

        ('OUTRO',         'Outro'),
    ]
    STATUS = [
        ('PENDENTE',   'Pendente'),
        ('PAGO',       'Pago'),
        ('ATRASADO',   'Atrasado'),
        ('CANCELADO',  'Cancelado'),
    ]

    descricao       = models.CharField(max_length=255)
    valor           = models.DecimalField(max_digits=12, decimal_places=2)
    data_vencimento = models.DateField()
    data_pagamento  = models.DateField(null=True, blank=True)
    categoria       = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    metodo          = models.CharField(max_length=20, choices=METODO_PAGAMENTO, default='TRANSFERENCIA')
    status          = models.CharField(max_length=15, choices=STATUS, default='PENDENTE')
    aluno           = models.ForeignKey(
        'core.Aluno',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transacoes',
    )
    # Referência opcional a qualquer objeto externo (FolhaPagamento.pk, etc.)
    referencia_externa_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        verbose_name        = 'Transação'
        verbose_name_plural = 'Transações'
        ordering            = ['-data_vencimento']

    def clean(self):
        if self.pk:
            original = Transacao.objects.get(pk=self.pk)
            if original.status == 'PAGO' and self.status == 'PAGO':
                if original.valor != self.valor:
                    raise ValidationError(
                        "Não é permitido alterar o valor de uma transação já paga."
                    )
        if self.categoria_id and self.categoria.tipo == 'DESPESA' and self.aluno_id:
            raise ValidationError("Despesas não devem estar associadas a alunos.")

    def save(self, *args, **kwargs):
        if self.status == 'PENDENTE' and self.data_vencimento < date.today():
            self.status = 'ATRASADO'
        if self.status == 'PAGO' and not self.data_pagamento:
            self.data_pagamento = date.today()
        super().save(*args, **kwargs)

    @property
    def is_overdue(self) -> bool:
        return self.status == 'ATRASADO' or (
            self.status == 'PENDENTE' and self.data_vencimento < date.today()
        )

    @property
    def tipo(self) -> str:
        return self.categoria.tipo

    def __str__(self):
        return f"{self.descricao} — {self.valor} MT"


# ──────────────────────────────────────────────
# FUNCIONARIO
# ──────────────────────────────────────────────

class Funcionario(models.Model):
    """
    Extensão financeira pura de um colaborador.

    Dados de identidade (nome, telefone, role) vivem em core.User e nos
    perfis de core (Motorista, Monitor, Gestor).  Aqui ficam apenas os
    dados financeiros: NUIT, salário base, subsídio, folha salarial.

    LIGAÇÕES AOS PERFIS DE CORE:
      Apenas UM dos três campos abaixo deve estar preenchido, determinado
      pelo role do User associado:
        MOTORISTA → motorista_perfil
        MONITOR   → monitor_perfil
        GESTOR    → gestor_perfil
        ADMIN / ADMINISTRATIVO → nenhum perfil

    CORRECÇÃO: os campos `cargo` e `telefone` foram removidos porque
      duplicavam User.role e PerfilMixin.telefone respectivamente.
      Para saber o cargo de um funcionário, usar funcionario.user.role.
      Para o telefone, usar funcionario.user.perfil_motorista.telefone (etc.).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_funcionario',
    )
    nuit = models.CharField(
        max_length=9,
        unique=True,
        help_text="Número de Identificação Tributária (9 dígitos)"
    )
    salario_base = models.DecimalField(max_digits=12, decimal_places=2)
    subsidio_transporte = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    ativo = models.BooleanField(default=True)
    data_admissao = models.DateField(auto_now_add=True)
    data_demissao = models.DateField(null=True, blank=True)

    # Ligações aos perfis de core (no máximo uma preenchida)
    motorista_perfil = models.OneToOneField(
        'core.Motorista',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dados_financeiros',
        help_text="Preencher apenas se o utilizador tiver role MOTORISTA"
    )
    monitor_perfil = models.OneToOneField(
        'core.Monitor',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dados_financeiros',
        help_text="Preencher apenas se o utilizador tiver role MONITOR"
    )
    gestor_perfil = models.OneToOneField(
        'core.Gestor',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dados_financeiros',
        help_text="Preencher apenas se o utilizador tiver role GESTOR"
    )

    class Meta:
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"

    # ------------------------------------------------------------------
    # Validações
    # ------------------------------------------------------------------

    def clean(self):
        # NUIT: exactamente 9 dígitos numéricos
        if self.nuit and (not self.nuit.isdigit() or len(self.nuit) != 9):
            raise ValidationError({'nuit': "O NUIT deve conter exactamente 9 dígitos numéricos."})

        # Mapeia role → campo de perfil esperado
        PERFIL_POR_ROLE = {
            'MOTORISTA': 'motorista_perfil',
            'MONITOR':   'monitor_perfil',
            'GESTOR':    'gestor_perfil',
        }
        TODOS_PERFIS = list(PERFIL_POR_ROLE.values())

        perfis_preenchidos = [c for c in TODOS_PERFIS if getattr(self, c)]

        # Nunca mais do que um perfil preenchido
        if len(perfis_preenchidos) > 1:
            raise ValidationError(
                "Um funcionário só pode estar associado a um perfil de core."
            )

        if not self.user_id:
            return

        role = self.user.role

        if role in PERFIL_POR_ROLE:
            campo_esperado = PERFIL_POR_ROLE[role]
            if not getattr(self, campo_esperado):
                raise ValidationError({
                    campo_esperado: (
                        f"Utilizadores com role {role} devem ter o perfil "
                        f"de {role.title()} associado."
                    )
                })
            # Garante que não foi preenchido o campo errado
            for campo in TODOS_PERFIS:
                if campo != campo_esperado and getattr(self, campo):
                    raise ValidationError({
                        campo: f"Este campo não deve ser preenchido para o role {role}."
                    })

        else:
            # ADMIN, ENCARREGADO, ALUNO — sem perfil associado
            if perfis_preenchidos:
                raise ValidationError(
                    f"Utilizadores com role {role} não têm perfil de core associado."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Soft delete — marca como inactivo e regista a data de demissão."""
        self.ativo         = False
        self.data_demissao = date.today()
        self.save()

    # ------------------------------------------------------------------
    # Properties / helpers
    # ------------------------------------------------------------------

    @property
    def salario_total(self) -> Decimal:
        base = self.salario_base or Decimal('0.00')
        subsidio = self.subsidio_transporte or Decimal('0.00')
        return base + subsidio

    @property
    def nome(self) -> str:
        return self.user.nome

    def __str__(self):
        return f"{self.user.nome} — {self.user.get_role_display()}"


# ──────────────────────────────────────────────
# MENSALIDADE MANAGER
# ──────────────────────────────────────────────

class MensalidadeManager(models.Manager):

    def total_devedor_mes(self, mes: int, ano: int) -> Decimal:
        resultado = (
            self.filter(mes_referente__month=mes, mes_referente__year=ano)
            .exclude(estado__in=['PAGO', 'ISENTO'])
            .aggregate(
                total_pendente=Sum(
                    F('valor_base') + F('multa_atraso') - F('desconto') - F('valor_pago_acumulado'),
                    output_field=models.DecimalField()
                )
            )
        )
        return resultado['total_pendente'] or Decimal('0.00')

    def resumo_estatistico(self, mes: int, ano: int):
        return (
            self.filter(mes_referente__month=mes, mes_referente__year=ano)
            .values('estado')
            .annotate(qtd=Count('id'))
        )

    def gerar_mensalidades_mes(self, mes: int, ano: int) -> int:
        """
        Gera mensalidades para todos os alunos activos sem registo
        para o mês/ano especificado.

        CORRECÇÃO: substituído bulk_create por create() individual.
        O bulk_create bypassa o save() do modelo, impedindo a geração
        automática do nr_fatura (campo unique obrigatório para auditoria).
        O custo de performance é negligenciável para o volume típico
        de alunos de uma escola.
        """
        from core.models import Aluno

        alunos_sem_mensalidade = Aluno.objects.filter(ativo=True).exclude(
            historico_mensalidades__mes_referente__month=mes,
            historico_mensalidades__mes_referente__year=ano,
        )
        data_ref = date(ano, mes, 1)
        criadas  = 0

        with transaction.atomic():
            for aluno in alunos_sem_mensalidade:
                self.create(
                    aluno=aluno,
                    mes_referente=data_ref,
                    valor_base=aluno.mensalidade,
                    estado='PENDENTE',
                )
                criadas += 1

        return criadas

    def aluno_tem_acesso_bloqueado(self, aluno) -> bool:
        """
        Verifica se o aluno tem 3 ou mais mensalidades em atraso.

        CORRECÇÃO: esta lógica foi movida de core.Aluno para cá,
        eliminando a dependência circular core → financeiro.
        Para verificar bloqueio: Mensalidade.objects.aluno_tem_acesso_bloqueado(aluno)
        """
        return (
            self.filter(
                aluno=aluno,
                estado='ATRASADO',
            ).count() >= 3
        )


# ──────────────────────────────────────────────
# MENSALIDADE
# ──────────────────────────────────────────────

class Mensalidade(models.Model):
    """
    Mensalidade de um aluno para um mês de referência.

    Ligações de saída:
      - aluno → core.Aluno (FK, PROTECT)
    """

    ESTADO_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO_PARCIAL', 'Pago Parcialmente'),
        ('PAGO', 'Pago Totalmente'),
        ('ATRASADO', 'Em Atraso'),
        ('ISENTO', 'Isento/Bolsa'),
    ]

    aluno = models.ForeignKey(
        'core.Aluno',
        on_delete=models.PROTECT,
        related_name='historico_mensalidades',
    )
    mes_referente = models.DateField(db_index=True)
    valor_base = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    multa_atraso = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    desconto = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    valor_pago_acumulado = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    data_ultimo_pagamento = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDENTE')
    nr_fatura = models.CharField(max_length=50, unique=True, null=True, blank=True)
    obs = models.TextField(blank=True, null=True)

    objects = MensalidadeManager()

    class Meta:
        unique_together = ('aluno', 'mes_referente')
        verbose_name = "Mensalidade"
        verbose_name_plural = "Mensalidades"
        ordering = ['-mes_referente']

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def valor_total_devido(self) -> Decimal:
        return max((self.valor_base + self.multa_atraso) - self.desconto, Decimal('0.00'))

    @property
    def saldo_devedor(self) -> Decimal:
        return max(self.valor_total_devido - self.valor_pago_acumulado, Decimal('0.00'))

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------

    def atualizar_estado(self):
        """
        Calcula o estado com base no saldo e na data limite configurada.
        Nunca altera estado ISENTO.
        """
        if self.estado == 'ISENTO':
            return

        if self.valor_pago_acumulado >= self.valor_total_devido:
            self.estado = 'PAGO'
        elif self.valor_pago_acumulado > 0:
            self.estado = 'PAGO_PARCIAL'
        else:
            config = ConfiguracaoFinanceira.get_solo()
            data_limite = config.data_limite_para_mes(self.mes_referente)
            self.estado = 'ATRASADO' if date.today() > data_limite else 'PENDENTE'

    # ------------------------------------------------------------------
    # Pagamento
    # ------------------------------------------------------------------

    def registrar_pagamento(self, valor, metodo: str):
        """Regista um pagamento (parcial ou total)."""
        valor_dec = Decimal(str(valor))
        if valor_dec <= 0:
            raise ValueError("O valor do pagamento deve ser positivo.")

        with transaction.atomic():
            obj = Mensalidade.objects.select_for_update().get(pk=self.pk)
            obj.valor_pago_acumulado += valor_dec
            obj.data_ultimo_pagamento = timezone.now()
            obj.atualizar_estado()
            obj.save()

            Transacao.objects.create(
                categoria=obj._get_categoria_mensalidade(),
                descricao=(
                    f"Mensalidade {obj.mes_referente.strftime('%m/%Y')} "
                    f"— {obj.aluno.user.nome}"
                ),
                valor=valor_dec,
                data_vencimento=obj.mes_referente,
                status='PAGO',
                metodo=metodo,
                aluno=obj.aluno,
            )

            if obj.estado == 'PAGO' and not Recibo.objects.filter(mensalidade=obj).exists():
                recibo = obj._gerar_recibo_automatico()
                # Disparar tasks assíncronas após criação do recibo
                if recibo:
                    try:
                        from financeiro.tasks import (
                            enviar_notificacao_pagamento,
                            gerar_pdf_recibo_task,
                            invalidar_cache_dashboard,
                        )
                        # Gerar PDF em background (não bloqueia o request)
                        gerar_pdf_recibo_task.delay(recibo.pk)
                        # Notificar encarregado
                        enviar_notificacao_pagamento.delay(obj.pk)
                        # Invalidar cache do dashboard
                        invalidar_cache_dashboard.delay()
                    except Exception:
                        # Se Celery não estiver disponível, continua sem erro
                        pass

    # ------------------------------------------------------------------
    # Multas
    # ------------------------------------------------------------------

    def verificar_e_aplicar_multa(self) -> bool:
        """Aplica a multa fixa se tiver passado do dia limite e ainda não foi aplicada."""
        if self.estado in ['PAGO', 'ISENTO'] or self.multa_atraso > 0:
            return False

        config = ConfiguracaoFinanceira.get_solo()
        data_limite = config.data_limite_para_mes(self.mes_referente)

        if date.today() > data_limite and self.saldo_devedor > 0:
            self.multa_atraso = config.valor_multa_fixa
            self.atualizar_estado()
            self.save(update_fields=['multa_atraso', 'estado'])
            return True
        return False

    # ------------------------------------------------------------------
    # Recibo
    # ------------------------------------------------------------------

    def _gerar_recibo_automatico(self) -> 'Recibo | None':
        if Recibo.objects.filter(mensalidade=self).exists():
            return None

        recibo = Recibo(mensalidade=self)
        recibo.save()  # gera codigo_recibo primeiro

        try:
            from financeiro.pdf_utils import gerar_pdf_recibo
            pdf_bytes = gerar_pdf_recibo(self, recibo)
            nome = f"recibo_{self.aluno.id}_{self.mes_referente.strftime('%Y%m')}.pdf"
            recibo.arquivo.save(nome, ContentFile(pdf_bytes), save=True)
        except Exception as exc:
            # Se o reportlab falhar, guarda fallback em texto
            import logging
            logging.getLogger(__name__).error(
                'Erro ao gerar PDF do recibo %s: %s', recibo.codigo_recibo, exc
            )
            conteudo = (
                f"RECIBO DE PAGAMENTO\n"
                f"Codigo : {recibo.codigo_recibo}\n"
                f"Aluno : {self.aluno.user.nome}\n"
                f"Mes : {self.mes_referente.strftime('%m/%Y')}\n"
                f"Valor : {self.valor_pago_acumulado} MT\n"
                f"Data : {date.today().strftime('%d/%m/%Y')}\n"
            )
            nome = f"recibo_{self.aluno.id}_{self.mes_referente.strftime('%Y%m')}.txt"
            recibo.arquivo.save(nome, ContentFile(conteudo.encode('utf-8')), save=True)

        return recibo

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_categoria_mensalidade(self) -> Categoria:
        cat, _ = Categoria.objects.get_or_create(nome='Mensalidade', tipo='RECEITA')
        return cat

    def save(self, *args, **kwargs):
        if self.mes_referente:
            self.mes_referente = self.mes_referente.replace(day=1)
        if not self.nr_fatura:
            self.nr_fatura = (
                f"FAT-{self.mes_referente.strftime('%Y%m')}"
                f"-{self.aluno_id}"
                f"-{uuid.uuid4().hex[:6].upper()}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.aluno.user.nome} — {self.mes_referente.strftime('%m/%Y')}"


# ──────────────────────────────────────────────
# LOG DE NOTIFICAÇÕES
# ──────────────────────────────────────────────

class LogNotificacoes(models.Model):
    mensalidade = models.ForeignKey(Mensalidade, on_delete=models.CASCADE, related_name='notificacoes')
    tipo = models.CharField(max_length=10, choices=[('SMS', 'SMS'), ('EMAIL', 'Email')])
    data_envio = models.DateTimeField(auto_now_add=True)
    sucesso = models.BooleanField(default=True)
    destino = models.CharField(max_length=100)
    resposta_server = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Log de Notificação"
        verbose_name_plural = "Logs de Notificação"
        ordering = ['-data_envio']

    def __str__(self):
        return f"{self.tipo} → {self.destino} ({'✓' if self.sucesso else '✗'})"


# ──────────────────────────────────────────────
# RECIBO
# ──────────────────────────────────────────────

class Recibo(models.Model):
    mensalidade = models.OneToOneField(
        Mensalidade,
        on_delete=models.CASCADE,
        related_name='recibo_emitido',
    )
    codigo_recibo = models.CharField(max_length=20, unique=True, editable=False)
    arquivo = models.FileField(upload_to='financeiro/recibos/%Y/%m', null=True, blank=True)
    data_emissao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Recibo"
        verbose_name_plural = "Recibos"

    def save(self, *args, **kwargs):
        if not self.codigo_recibo:
            while True:
                codigo = f'REC-{date.today().year}-{uuid.uuid4().hex[:4].upper()}'
                if not Recibo.objects.filter(codigo_recibo=codigo).exists():
                    self.codigo_recibo = codigo
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Recibo {self.codigo_recibo} — {self.mensalidade.aluno.user.nome}"


# ──────────────────────────────────────────────
# FOLHA DE PAGAMENTO
# ──────────────────────────────────────────────

class FolhaPagamento(models.Model):
    """
    Folha de pagamento mensal de um funcionário.

    Ligações de saída:
      - funcionario       → Funcionario (FK, PROTECT)
      - transacao_vinculada → Transacao (OneToOne, SET_NULL)
    """

    STATUS_CHOICES = [('PENDENTE', 'Pendente'), ('PAGO', 'Pago')]

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.PROTECT, related_name='pagamentos'
    )
    mes_referente = models.DateField(help_text="Primeiro dia do mês correspondente")
    data_processamento = models.DateTimeField(auto_now_add=True)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDENTE')
    transacao_vinculada = models.OneToOneField(
        Transacao,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )

    class Meta:
        unique_together = ('funcionario', 'mes_referente')
        verbose_name = "Folha de Pagamento"
        verbose_name_plural = "Folhas de Pagamento"

    def confirmar_pagamento(self, metodo: str = 'TRANSFERENCIA'):
        """Gera a transação de despesa e marca como pago."""
        if self.status == 'PAGO':
            return

        with transaction.atomic():
            categoria, _ = Categoria.objects.get_or_create(nome='Salários', tipo='DESPESA')
            nova_transacao = Transacao.objects.create(
                descricao=(
                    f"Salário {self.mes_referente.strftime('%m/%Y')} "
                    f"— {self.funcionario.user.nome}"
                ),
                valor=self.valor_total,
                data_vencimento=date.today(),
                data_pagamento=date.today(),
                categoria=categoria,
                metodo=metodo,
                status='PAGO',
                referencia_externa_id=self.pk,  # pk da FolhaPagamento para rastreabilidade
            )
            self.transacao_vinculada = nova_transacao
            self.status = 'PAGO'
            self.save()

    def save(self, *args, **kwargs):
        if self.mes_referente:
            self.mes_referente = self.mes_referente.replace(day=1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Salário {self.mes_referente.strftime('%m/%Y')} — {self.funcionario.user.nome}"


# ──────────────────────────────────────────────
# DESPESA DE VEÍCULO
# ──────────────────────────────────────────────

class DespesaVeiculo(models.Model):
    """
    Despesa operacional de um veículo.

    Fonte única de verdade para veículos: transporte.Veiculo.
    Campo 'matricula' em vez de 'placa'.

    Ligações de saída:
      - veiculo   → transporte.Veiculo (FK, CASCADE)
      - transacao → Transacao (OneToOne, SET_NULL)
    """

    TIPO_DESPESA = [
        ('COMBUSTIVEL', 'Combustível'),
        ('MANUTENCAO', 'Manutenção/Oficina'),
        ('DOCUMENTACAO', 'Seguros/Inspecção/Taxas'),
        ('LIMPEZA', 'Lavagem/Limpeza'),
    ]

    veiculo   = models.ForeignKey(
        'transporte.Veiculo',
        on_delete=models.CASCADE,
        related_name='gastos',
    )
    tipo = models.CharField(max_length=20, choices=TIPO_DESPESA)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField(default=date.today)
    km_atual  = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Quilometragem para controlo de consumo"
    )
    transacao = models.OneToOneField(
        Transacao,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='despesa_veiculo',
    )

    class Meta:
        verbose_name = "Despesa de Veículo"
        verbose_name_plural = "Despesas de Veículos"
        ordering = ['-data']

    def clean(self):
        if self.pk:
            original = DespesaVeiculo.objects.get(pk=self.pk)
            if original.valor != self.valor:
                raise ValidationError("Não é permitido alterar o valor de uma despesa já registada.")

    def save(self, *args, **kwargs):
        self.full_clean()
        is_new = self.pk is None

        with transaction.atomic():
            super().save(*args, **kwargs)
            if is_new:
                cat, _ = Categoria.objects.get_or_create(nome='Operacional Frota', tipo='DESPESA')
                nova_transacao = Transacao.objects.create(
                    descricao=f"{self.get_tipo_display()} — {self.veiculo.matricula}",
                    valor=self.valor,
                    data_vencimento=self.data,
                    data_pagamento=self.data,
                    categoria=cat,
                    status='PAGO',
                )
                DespesaVeiculo.objects.filter(pk=self.pk).update(transacao=nova_transacao)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Despesas da frota não podem ser eliminadas. Utilize um estorno se necessário."
        )

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.veiculo.matricula} ({self.valor} MT)"


# ──────────────────────────────────────────────
# DESPESA GERAL
# ──────────────────────────────────────────────

class DespesaGeral(models.Model):
    """Despesa operacional geral (aluguer, electricidade, etc.)."""

    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    pago = models.BooleanField(default=False)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        limit_choices_to={'tipo': 'DESPESA'},
    )
    transacao = models.OneToOneField(
        Transacao,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='despesa_geral',
    )

    class Meta:
        verbose_name = "Despesa Geral"
        verbose_name_plural = "Despesas Gerais"
        ordering = ['-data_vencimento']

    def registrar_pagamento(self, metodo: str = 'DINHEIRO'):
        if self.pago:
            return

        with transaction.atomic():
            self.pago = True
            self.save()
            nova_transacao = Transacao.objects.create(
                descricao=f"PAGAMENTO: {self.descricao}",
                valor=self.valor,
                data_vencimento=self.data_vencimento,
                data_pagamento=date.today(),
                categoria=self.categoria,
                status='PAGO',
                metodo=metodo,
            )
            DespesaGeral.objects.filter(pk=self.pk).update(transacao=nova_transacao)

    def save(self, *args, **kwargs):
        if self.pk:
            original = DespesaGeral.objects.get(pk=self.pk)
            if original.pago and original.valor != self.valor:
                raise ValidationError("Não é permitido alterar o valor de uma despesa já paga.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.pago:
            raise ValidationError(
                "Esta despesa está paga e não pode ser eliminada."
            )
        super().delete(*args, **kwargs)

    def __str__(self):
        estado = "Paga" if self.pago else "Pendente"
        return f"{self.descricao} — {self.valor} MT ({estado})"


# ──────────────────────────────────────────────
# BALANÇO MENSAL
# ──────────────────────────────────────────────

class BalancoMensal(models.Model):
    """Fecho financeiro mensal agregando receitas e despesas."""

    mes_referencia = models.DateField(unique=True, help_text="Primeiro dia do mês")
    data_fecho = models.DateTimeField(auto_now_add=True)
    transacao = models.OneToOneField(
        Transacao,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='balanco_mensal',
    )

    # Receitas
    total_receitas_previstas = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_receitas_pagas = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Despesas (detalhadas)
    total_despesas_gerais = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_despesas_frota = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_folha_salarial = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Resultado
    lucro_prejuizo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    finalizado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Balanço Mensal"
        verbose_name_plural = "Balanços Mensais"
        ordering = ['-mes_referencia']

    @classmethod
    def gerar_balanco(cls, mes: int, ano: int) -> 'BalancoMensal':
        """
        Calcula e persiste os totais de todas as tabelas financeiras
        para o mês indicado. Cria também uma Transação de resumo.
        """
        data_ref = date(ano, mes, 1)

        mensalidades = Mensalidade.objects.filter(
            mes_referente__month=mes, mes_referente__year=ano
        )
        previsto = mensalidades.aggregate(s=Sum('valor_base'))['s'] or Decimal('0.00')
        pagas    = (
            mensalidades.filter(estado='PAGO')
            .aggregate(s=Sum('valor_pago_acumulado'))['s'] or Decimal('0.00')
        )
        gerais   = (
            DespesaGeral.objects
            .filter(pago=True, data_vencimento__month=mes, data_vencimento__year=ano)
            .aggregate(s=Sum('valor'))['s'] or Decimal('0.00')
        )
        frota    = (
            DespesaVeiculo.objects
            .filter(data__month=mes, data__year=ano)
            .aggregate(s=Sum('valor'))['s'] or Decimal('0.00')
        )
        salarios = (
            FolhaPagamento.objects
            .filter(status='PAGO', mes_referente__month=mes, mes_referente__year=ano)
            .aggregate(s=Sum('valor_total'))['s'] or Decimal('0.00')
        )

        total_saidas = gerais + frota + salarios
        resultado = pagas - total_saidas

        with transaction.atomic():
            obj, _ = cls.objects.update_or_create(
                mes_referencia=data_ref,
                defaults={
                    'total_receitas_previstas': previsto,
                    'total_receitas_pagas': pagas,
                    'total_despesas_gerais': gerais,
                    'total_despesas_frota': frota,
                    'total_folha_salarial': salarios,
                    'lucro_prejuizo': resultado,
                    'finalizado': True,
                }
            )

            # Categoria fixa de tipo RECEITA — o sinal do valor (positivo/negativo)
            # indica lucro ou prejuízo. Evita criar duas categorias 'Balanço Mensal'.
            cat_resumo, _ = Categoria.objects.get_or_create(
                nome='Balanço Mensal',
                tipo='RECEITA',
            )
            descricao_bal = (
                f"Balanço {data_ref.strftime('%m/%Y')} — "
                f"Resultado: {resultado} MT"
            )

            if obj.transacao:
                Transacao.objects.filter(pk=obj.transacao_id).update(
                    descricao=descricao_bal,
                    valor=abs(resultado),
                    data_vencimento=data_ref,
                    status='PAGO',
                )
            else:
                nova_transacao = Transacao.objects.create(
                    descricao=descricao_bal,
                    valor=abs(resultado),
                    data_vencimento=data_ref,
                    data_pagamento=date.today(),
                    categoria=cat_resumo,
                    status='PAGO',
                )
                cls.objects.filter(pk=obj.pk).update(transacao=nova_transacao)
                obj.refresh_from_db()

        # Invalidar cache do dashboard após novo balanço
        try:
            from financeiro.tasks import invalidar_cache_dashboard
            invalidar_cache_dashboard.delay()
        except Exception:
            pass

        return obj

    def __str__(self):
        return f"Balanço {self.mes_referencia.strftime('%m/%Y')}"
