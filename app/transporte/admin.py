"""
transporte/admin.py
===================
Administração Django para o módulo transporte.

Registos: Veiculo, Rota, TransporteAluno, Manutencao, Abastecimento
"""

from django.contrib import admin
from django.utils.html import format_html
from transporte.models import Abastecimento, Manutencao, Rota, TransporteAluno, Veiculo


def _badge_bool(valor, label_sim='Sim', label_nao='Não'):
    if valor:
        return format_html('<span style="color:#16a34a;font-weight:600;">● {}</span>', label_sim)
    return format_html('<span style="color:#dc2626;font-weight:600;">● {}</span>', label_nao)


class RotaInline(admin.TabularInline):
    model = Rota
    extra = 0
    show_change_link = True
    fields = ('nome', 'hora_partida', 'hora_chegada', 'ativo')
    readonly_fields = ('nome', 'hora_partida', 'hora_chegada', 'ativo')
    can_delete = False


class ManutencaoInline(admin.TabularInline):
    model = Manutencao
    extra = 0
    show_change_link = True
    fields = ('tipo', 'descricao', 'data_inicio', 'custo', 'concluida')
    readonly_fields = ('data_inicio', 'custo', 'concluida')


class AbastecimentoInline(admin.TabularInline):
    model = Abastecimento
    extra = 0
    show_change_link = True
    fields = ('data', 'quilometragem_no_ato', 'quantidade_litros', 'custo_total', 'posto_combustivel')
    readonly_fields = ('data',)


class TransporteAlunoInline(admin.TabularInline):
    model = TransporteAluno
    extra = 0
    fields = ('aluno', 'status', 'data')
    readonly_fields = ('data',)
    autocomplete_fields = ('aluno',)


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = (
        'matricula', 'marca', 'modelo', 'motorista', 'capacidade', 'vagas_display', 'doc_display', 'manutencao_display', 'ativo_display',
    )
    list_filter = ('ativo', 'marca')
    search_fields = ('matricula', 'marca', 'modelo', 'motorista__user__nome')
    readonly_fields = (
        'vagas_disponiveis', 'custo_total_combustivel', 'autonomia_estimada',
        'consumo_medio_display', 'custo_km_display',
        'em_manutencao_display', 'precisa_manutencao_display',
        'doc_em_dia_display',
        'criado_em', 'atualizado_em',
    )
    autocomplete_fields = ('motorista',)
    inlines = [RotaInline, ManutencaoInline, AbastecimentoInline]

    fieldsets = (
        ('Identificação', {
            'fields': ('marca', 'modelo', 'matricula', 'motorista', 'ativo')
        }),
        ('Capacidade', {
            'fields': ('capacidade', 'capacidade_tanque', 'vagas_disponiveis')
        }),
        ('Quilometragem', {
            'fields': (
                'quilometragem_atual', 'data_ultima_revisao', 'km_proxima_revisao',
                'precisa_manutencao_display', 'em_manutencao_display',
            )
        }),
        ('Documentação', {
            'fields': (
                'data_validade_seguro', 'data_validade_inspecao',
                'nr_manifesto', 'data_validade_manifesto',
                'doc_em_dia_display',
            )
        }),
        ('Indicadores de Custo', {
            'fields': (
                'custo_total_combustivel', 'autonomia_estimada',
                'consumo_medio_display', 'custo_km_display',
            ),
            'classes': ('collapse',),
        }),
        ('Auditoria', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',),
        }),
    )

    # ── list_display helpers ──

    @admin.display(description='Vagas')
    def vagas_display(self, obj):
        return f"{obj.vagas_disponiveis}/{obj.capacidade}"

    @admin.display(description='Documentos')
    def doc_display(self, obj):
        return _badge_bool(obj.document_em_dia(), 'OK', 'Vencido')

    @admin.display(description='Manutenção')
    def manutencao_display(self, obj):
        if obj.em_manutencao():
            return format_html('<span style="color:#f59e0b;font-weight:600;">● Em manutenção</span>')
        if obj.precisa_manutencao():
            return format_html('<span style="color:#dc2626;font-weight:600;">● Revisão urgente</span>')
        return format_html('<span style="color:#16a34a;font-weight:600;">● OK</span>')

    @admin.display(description='Estado')
    def ativo_display(self, obj):
        return _badge_bool(obj.ativo, 'Activo', 'Inactivo')

    # ── readonly fieldset helpers ──

    @admin.display(description='Consumo médio (km/L)')
    def consumo_medio_display(self, obj):
        v = obj.consumo_medio()
        return f"{v:.2f} km/L" if v else '—'

    @admin.display(description='Custo por km (MT)')
    def custo_km_display(self, obj):
        v = obj.custo_por_quilometro()
        return f"{v:.2f} MT/km" if v else '—'

    @admin.display(description='Em manutenção?')
    def em_manutencao_display(self, obj):
        return _badge_bool(obj.em_manutencao(), 'Sim', 'Não')

    @admin.display(description='Precisa revisão?')
    def precisa_manutencao_display(self, obj):
        return _badge_bool(obj.precisa_manutencao(), 'Sim', 'Não')

    @admin.display(description='Documentação em dia?')
    def doc_em_dia_display(self, obj):
        return _badge_bool(obj.document_em_dia(), 'Sim', 'Não')


@admin.register(Rota)
class RotaAdmin(admin.ModelAdmin):
    list_display = (
        'nome', 'veiculo', 'motorista_display',
        'hora_partida', 'hora_chegada',
        'total_inscritos_display', 'vagas_display', 'ativo_display',
    )
    list_filter = ('ativo', 'veiculo__marca')
    search_fields = ('nome', 'veiculo__matricula', 'veiculo__motorista__user__nome')
    readonly_fields = ('total_inscritos', 'motorista_display', 'criado_em', 'atualizado_em')
    autocomplete_fields = ('veiculo',)
    filter_horizontal = ('alunos',)
    inlines = [TransporteAlunoInline]

    fieldsets = (
        ('Identificação', {
            'fields': ('nome', 'descricao', 'ativo')
        }),
        ('Veículo e Motorista', {
            'fields': ('veiculo', 'motorista_display')
        }),
        ('Horário', {
            'fields': ('hora_partida', 'hora_chegada')
        }),
        ('Alunos', {
            'fields': ('alunos', 'total_inscritos')
        }),
        ('Auditoria', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Motorista')
    def motorista_display(self, obj):
        m = obj.motorista
        return m.user.nome if m else '—'

    @admin.display(description='Inscritos')
    def total_inscritos_display(self, obj):
        return obj.total_inscritos

    @admin.display(description='Vagas')
    def vagas_display(self, obj):
        return obj.veiculo.vagas_disponiveis

    @admin.display(description='Estado')
    def ativo_display(self, obj):
        return _badge_bool(obj.ativo, 'Activa', 'Inactiva')


@admin.register(TransporteAluno)
class TransporteAlunoAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'rota', 'status', 'data')
    list_filter = ('status', 'data', 'rota')
    search_fields = ('aluno__user__nome', 'rota__nome')
    readonly_fields = ('data',)
    date_hierarchy = 'data'
    autocomplete_fields = ('aluno', 'rota')

    fieldsets = (
        (None, {
            'fields': ('aluno', 'rota', 'status', 'data')
        }),
    )


@admin.register(Manutencao)
class ManutencaoAdmin(admin.ModelAdmin):
    list_display = (
        'veiculo', 'tipo', 'descricao_curta',
        'data_inicio', 'data_fim', 'custo', 'concluida_display',
    )
    list_filter = ('concluida', 'tipo', 'veiculo__marca')
    search_fields = ('veiculo__matricula', 'descricao')
    readonly_fields = ('data_fim',)
    autocomplete_fields = ('veiculo',)
    date_hierarchy = 'data_inicio'

    fieldsets = (
        ('Veículo', {
            'fields': ('veiculo', 'tipo')
        }),
        ('Serviço', {
            'fields': ('descricao', 'custo')
        }),
        ('Datas e Quilometragem', {
            'fields': (
                'data_inicio', 'data_fim',
                'quilometragem_no_momento_revisao', 'km_proxima_revisao',
            )
        }),
        ('Estado', {
            'fields': ('concluida',)
        }),
    )

    @admin.display(description='Descrição')
    def descricao_curta(self, obj):
        return obj.descricao[:50] + ('…' if len(obj.descricao) > 50 else '')

    @admin.display(description='Concluída')
    def concluida_display(self, obj):
        return _badge_bool(obj.concluida, 'Sim', 'Não')


@admin.register(Abastecimento)
class AbastecimentoAdmin(admin.ModelAdmin):
    list_display = (
        'veiculo', 'data', 'quilometragem_no_ato',
        'quantidade_litros', 'custo_total', 'posto_combustivel',
    )
    list_filter = ('data', 'posto_combustivel', 'veiculo__marca')
    search_fields = ('veiculo__matricula', 'posto_combustivel')
    readonly_fields = ('data',)
    autocomplete_fields = ('veiculo',)
    date_hierarchy = 'data'

    fieldsets = (
        ('Veículo', {
            'fields': ('veiculo', 'data')
        }),
        ('Abastecimento', {
            'fields': (
                'quilometragem_no_ato', 'quantidade_litros',
                'custo_total', 'posto_combustivel',
            )
        }),
    )
