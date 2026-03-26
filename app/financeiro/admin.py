"""
financeiro/admin.py
===================
Administração Django para o módulo financeiro.

Registos: ConfiguracaoFinanceira, Categoria, Transacao,
          Funcionario, Mensalidade, Recibo, LogNotificacoes,
          FolhaPagamento, DespesaVeiculo, DespesaGeral, BalancoMensal
"""

from datetime import date

from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html

from financeiro.models import (
    BalancoMensal,
    Categoria,
    ConfiguracaoFinanceira,
    DespesaGeral,
    DespesaVeiculo,
    FolhaPagamento,
    Funcionario,
    LogNotificacoes,
    Mensalidade,
    Recibo,
    Transacao,
)


def _badge(valor, label_sim, label_nao, cor_sim='#16a34a', cor_nao='#dc2626'):
    cor = cor_sim if valor else cor_nao
    label = label_sim if valor else label_nao
    return format_html('<span style="color:{};font-weight:600;">● {}</span>', cor, label)


def _badge_status_transacao(status):
    CORES = {
        'PAGO': '#16a34a',
        'PENDENTE': '#f59e0b',
        'ATRASADO': '#dc2626',
        'CANCELADO': '#6b7280',
    }
    cor = CORES.get(status, '#6b7280')
    return format_html('<span style="color:{};font-weight:600;">● {}</span>', cor, status)


@admin.register(ConfiguracaoFinanceira)
class ConfiguracaoFinanceiraAdmin(admin.ModelAdmin):
    """
    Singleton — apenas um registo existe.
    Botão de eliminar desactivado na interface.
    """
    list_display = ('__str__', 'dia_vencimento', 'dia_limite_pagamento', 'valor_multa_fixa')
    fieldsets = (
        ('Datas de Pagamento', {
            'fields': ('dia_vencimento', 'dia_limite_pagamento'),
            'description': 'Dias do mês aplicados a todos os alunos.'
        }),
        ('Multas', {
            'fields': ('valor_multa_fixa',)
        }),
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return not ConfiguracaoFinanceira.objects.exists()


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_display')
    list_filter = ('tipo',)
    search_fields = ('nome',)

    @admin.display(description='Tipo')
    def tipo_display(self, obj):
        if obj.tipo == 'RECEITA':
            return format_html('<span style="color:#16a34a;font-weight:600;">↑ Receita</span>')
        return format_html('<span style="color:#dc2626;font-weight:600;">↓ Despesa</span>')


@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    list_display = (
        'descricao', 'valor_display', 'tipo_display',
        'data_vencimento', 'data_pagamento',
        'metodo', 'status_display', 'aluno',
    )
    list_filter = ('status', 'metodo', 'categoria__tipo', 'categoria')
    search_fields = ('descricao', 'aluno__user__nome')
    readonly_fields = ('data_pagamento', 'tipo_display', 'is_overdue')
    date_hierarchy = 'data_vencimento'

    fieldsets = (
        ('Transação', {
            'fields': ('descricao', 'valor', 'categoria', 'metodo')
        }),
        ('Datas e Estado', {
            'fields': ('data_vencimento', 'data_pagamento', 'status')
        }),
        ('Ligações', {
            'fields': ('aluno', 'referencia_externa_id'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Valor')
    def valor_display(self, obj):
        cor = '#16a34a' if obj.tipo == 'RECEITA' else '#dc2626'
        sinal = '+' if obj.tipo == 'RECEITA' else '-'
        return format_html(
            '<span style="color:{};font-weight:600;">{}{} MT</span>',
            cor, sinal, obj.valor
        )

    @admin.display(description='Tipo')
    def tipo_display(self, obj):
        if obj.tipo == 'RECEITA':
            return format_html('<span style="color:#16a34a;font-weight:600;">↑ Receita</span>')
        return format_html('<span style="color:#dc2626;font-weight:600;">↓ Despesa</span>')

    @admin.display(description='Estado')
    def status_display(self, obj):
        return _badge_status_transacao(obj.status)

    def has_delete_permission(self, request, obj=None):
        """Transações pagas não podem ser eliminadas."""
        if obj and obj.status == 'PAGO':
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('nome_display', 'role_display', 'nuit', 'salario_base', 'subsidio_transporte', 'salario_total_display', 'ativo_display',)
    list_filter = ('ativo', 'user__role')
    search_fields = ('user__nome', 'user__email', 'nuit')
    readonly_fields = (
        'salario_total_display', 'data_admissao', 'data_demissao',
    )
    autocomplete_fields = ('user', 'motorista_perfil', 'monitor_perfil', 'gestor_perfil')

    fieldsets = (
        ('Utilizador', {
            'fields': ('user', 'ativo')
        }),
        ('Dados Fiscais', {
            'fields': ('nuit',)
        }),
        ('Remuneração', {
            'fields': ('salario_base', 'subsidio_transporte', 'salario_total_display')
        }),
        ('Perfis de Core', {
            'fields': ('motorista_perfil', 'monitor_perfil', 'gestor_perfil'),
            'description': 'Apenas um campo deve ser preenchido, de acordo com o role do utilizador.',
            'classes': ('collapse',),
        }),
        ('Admissão / Demissão', {
            'fields': ('data_admissao', 'data_demissao'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Nome')
    def nome_display(self, obj):
        return obj.user.nome

    @admin.display(description='Cargo')
    def role_display(self, obj):
        return obj.user.get_role_display()

    @admin.display(description='Salário Total', ordering='salario_base')
    def salario_total_display(self, obj):
        return f"{obj.salario_total: 2f} MT"

    @admin.display(description='Estado')
    def ativo_display(self, obj):
        return _badge(obj.ativo, 'Activo', 'Inactivo')

    def has_delete_permission(self, request, obj=None):
        """Usa soft delete — não permite eliminação real."""
        return False


class LogNotificacoesInline(admin.TabularInline):
    model= LogNotificacoes
    extra= 0
    can_delete= False
    readonly_fields = ('tipo', 'data_envio', 'sucesso', 'destino', 'resposta_server')

    def has_add_permission(self, request, obj=None):
        return False


class ReciboInline(admin.StackedInline):
    model= Recibo
    extra = 0
    can_delete = False
    readonly_fields = ('codigo_recibo', 'arquivo', 'data_emissao')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Mensalidade)
class MensalidadeAdmin(admin.ModelAdmin):
    list_display = (
        'aluno', 'mes_referente_display',
        'valor_base', 'multa_atraso', 'desconto',
        'valor_pago_acumulado', 'saldo_devedor_display',
        'estado_display',
    )
    list_filter = ('estado', 'mes_referente')
    search_fields = ('aluno__user__nome', 'nr_fatura')
    readonly_fields = (
        'nr_fatura', 'saldo_devedor', 'valor_total_devido',
        'data_ultimo_pagamento',
    )
    date_hierarchy = 'mes_referente'
    inlines = [ReciboInline, LogNotificacoesInline]
    autocomplete_fields = ('aluno',)

    fieldsets = (
        ('Aluno e Mês', {
            'fields': ('aluno', 'mes_referente', 'nr_fatura')
        }),
        ('Valores', {
            'fields': (
                'valor_base', 'multa_atraso', 'desconto',
                    'valor_total_devido',
                'valor_pago_acumulado', 'saldo_devedor',
                'data_ultimo_pagamento',
            )
        }),
        ('Estado', {
            'fields': ('estado', 'obs')
        }),
    )

    @admin.display(description='Mês')
    def mes_referente_display(self, obj):
        return obj.mes_referente.strftime('%m/%Y')

    @admin.display(description='Saldo devedor')
    def saldo_devedor_display(self, obj):
        saldo = obj.saldo_devedor
        if saldo > 0:
            return format_html('<span style="color:#dc2626;font-weight:600;">{} MT</span>', saldo)
        return format_html('<span style="color:#16a34a;">0.00 MT</span>')

    @admin.display(description='Estado')
    def estado_display(self, obj):
        CORES = {
            'PAGO': '#16a34a',
            'PAGO_PARCIAL': '#f59e0b',
            'PENDENTE': '#3b82f6',
            'ATRASADO': '#dc2626',
            'ISENTO': '#6b7280',
        }
        cor = CORES.get(obj.estado, '#6b7280')
        return format_html(
            '<span style="color:{};font-weight:600;">● {}</span>',
            cor, obj.get_estado_display()
        )

    actions = ['aplicar_multas', 'gerar_mensalidades_mes_atual']

    @admin.action(description='Aplicar multas às mensalidades em atraso seleccionadas')
    def aplicar_multas(self, request, queryset):
        aplicadas = sum(1 for m in queryset if m.verificar_e_aplicar_multa())
        self.message_user(request, f'{aplicadas} multa(s) aplicada(s).')

    @admin.action(description='Gerar mensalidades para o mês actual (alunos sem registo)')
    def gerar_mensalidades_mes_atual(self, request, queryset):
        hoje = date.today()
        total = Mensalidade.objects.gerar_mensalidades_mes(hoje.month, hoje.year)
        self.message_user(request, f'{total} mensalidade(s) gerada(s) para {hoje.strftime("%m/%Y")}.')


@admin.register(Recibo)
class ReciboAdmin(admin.ModelAdmin):
    list_display = ('codigo_recibo', 'mensalidade', 'aluno_display', 'data_emissao')
    search_fields = ('codigo_recibo', 'mensalidade__aluno__user__nome')
    readonly_fields = ('codigo_recibo', 'data_emissao')
    date_hierarchy = 'data_emissao'

    @admin.display(description='Aluno')
    def aluno_display(self, obj):
        return obj.mensalidade.aluno.user.nome

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FolhaPagamento)
class FolhaPagamentoAdmin(admin.ModelAdmin):
    list_display = (
        'funcionario', 'mes_referente_display',
        'valor_total', 'status_display', 'data_processamento',
    )
    list_filter = ('status', 'mes_referente')
    search_fields = ('funcionario__user__nome',)
    readonly_fields = ('data_processamento', 'transacao_vinculada')
    date_hierarchy = 'mes_referente'
    autocomplete_fields = ('funcionario',)

    fieldsets = (
        ('Funcionário', {
            'fields': ('funcionario', 'mes_referente')
        }),
        ('Pagamento', {
            'fields': ('valor_total', 'status', 'data_processamento', 'transacao_vinculada')
        }),
    )

    @admin.display(description='Mês')
    def mes_referente_display(self, obj):
        return obj.mes_referente.strftime('%m/%Y')

    @admin.display(description='Estado')
    def status_display(self, obj):
        return _badge(obj.status == 'PAGO', 'Pago', 'Pendente')

    actions = ['confirmar_pagamento']

    @admin.action(description='Confirmar pagamento das folhas seleccionadas (Transferência)')
    def confirmar_pagamento(self, request, queryset):
        confirmadas = 0
        for folha in queryset.filter(status='PENDENTE'):
            folha.confirmar_pagamento(metodo='TRANSFERENCIA')
            confirmadas += 1
        self.message_user(request, f'{confirmadas} folha(s) confirmada(s).')


@admin.register(DespesaVeiculo)
class DespesaVeiculoAdmin(admin.ModelAdmin):
    list_display = ('veiculo', 'tipo', 'valor', 'data', 'km_atual', 'transacao')
    list_filter = ('tipo', 'data', 'veiculo__marca')
    search_fields = ('veiculo__matricula',)
    readonly_fields = ('transacao',)
    date_hierarchy = 'data'
    autocomplete_fields = ('veiculo',)

    fieldsets = (
        ('Veículo', {
            'fields': ('veiculo', 'tipo', 'data', 'km_atual')
        }),
        ('Valor', {
            'fields': ('valor', 'transacao')
        }),
    )

    def has_delete_permission(self, request, obj=None):
        """Despesas de frota não podem ser eliminadas."""
        return False


@admin.register(DespesaGeral)
class DespesaGeralAdmin(admin.ModelAdmin):
    list_display = (
        'descricao', 'valor', 'categoria',
        'data_vencimento', 'pago_display', 'transacao',
    )
    list_filter = ('pago', 'categoria', 'data_vencimento')
    search_fields = ('descricao',)
    readonly_fields = ('transacao',)
    date_hierarchy = 'data_vencimento'

    fieldsets = (
        ('Despesa', {
            'fields': ('descricao', 'categoria', 'valor', 'data_vencimento')
        }),
        ('Pagamento', {
            'fields': ('pago', 'transacao')
        }),
    )

    @admin.display(description='Pago?')
    def pago_display(self, obj):
        return _badge(obj.pago, 'Pago', 'Pendente')

    actions = ['registar_pagamento']

    @admin.action(description='Registar pagamento das despesas seleccionadas')
    def registar_pagamento(self, request, queryset):
        pagas = 0
        for despesa in queryset.filter(pago=False):
            despesa.registrar_pagamento(metodo='DINHEIRO')
            pagas += 1
        self.message_user(request, f'{pagas} despesa(s) marcada(s) como paga(s).')

    def has_delete_permission(self, request, obj=None):
        if obj and obj.pago:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(BalancoMensal)
class BalancoMensalAdmin(admin.ModelAdmin):
    list_display = (
        'mes_referencia_display',
        'total_receitas_pagas', 'total_despesas_display',
        'lucro_prejuizo_display', 'finalizado_display',
        'data_fecho',
    )
    list_filter = ('finalizado',)
    readonly_fields = (
        'mes_referencia', 'data_fecho', 'transacao',
        'total_receitas_previstas', 'total_receitas_pagas',
        'total_despesas_gerais', 'total_despesas_frota',
        'total_folha_salarial', 'lucro_prejuizo', 'finalizado',
    )
    date_hierarchy = 'mes_referencia'

    fieldsets = (
        ('Mês', {
            'fields': ('mes_referencia', 'data_fecho', 'finalizado', 'transacao')
        }),
        ('Receitas', {
            'fields': ('total_receitas_previstas', 'total_receitas_pagas')
        }),
        ('Despesas', {
            'fields': ('total_despesas_gerais', 'total_despesas_frota', 'total_folha_salarial')
        }),
        ('Resultado', {
            'fields': ('lucro_prejuizo',)
        }),
    )

    @admin.display(description='Mês')
    def mes_referencia_display(self, obj):
        return obj.mes_referencia.strftime('%m/%Y')

    @admin.display(description='Total Despesas')
    def total_despesas_display(self, obj):
        total = obj.total_despesas_gerais + obj.total_despesas_frota + obj.total_folha_salarial
        return f"{total} MT"

    @admin.display(description='Resultado')
    def lucro_prejuizo_display(self, obj):
        if obj.lucro_prejuizo >= 0:
            return format_html(
                '<span style="color:#16a34a;font-weight:600;">+{} MT</span>',
                obj.lucro_prejuizo
            )
        return format_html(
            '<span style="color:#dc2626;font-weight:600;">{} MT</span>',
            obj.lucro_prejuizo
        )

    @admin.display(description='Fechado?')
    def finalizado_display(self, obj):
        return _badge(obj.finalizado, 'Fechado', 'Em aberto', '#16a34a', '#f59e0b')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    actions = ['gerar_balanco_action']

    @admin.action(description='Re-calcular balanço para o(s) mês(es) seleccionado(s)')
    def gerar_balanco_action(self, request, queryset):
        for balanco in queryset:
            BalancoMensal.gerar_balanco(
                balanco.mes_referencia.month,
                balanco.mes_referencia.year,
            )
        self.message_user(request, f'{queryset.count()} balanço(s) recalculado(s).')
