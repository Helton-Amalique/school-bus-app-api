"""
core/admin.py
Administração Django para o módulo core.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from core.models import Aluno, Encarregado, Gestor, Monitor, Motorista, User


def _badge_ativo(obj):
    """Ícone visual para o campo `ativo` nas list_display."""
    if obj.ativo:
        return format_html('<span style="color:#16a34a;font-weight:600;">● Activo</span>')
    return format_html('<span style="color:#dc2626;font-weight:600;">● Inactivo</span>')

_badge_ativo.short_description = "Estado"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin para o modelo User customizado (sem username, com role).
    Estende BaseUserAdmin substituindo os fieldsets que referenciam username.
    """

    ordering = ('nome',)
    list_display = ('email', 'nome', 'role', 'is_active', 'is_staff', 'data_criacao')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'nome')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'last_login')

    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        (_('Informação Pessoal'), {
            'fields': ('nome', 'role')
        }),
        (_('Permissões'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        (_('Datas'), {
            'fields': ('data_criacao', 'data_atualizacao', 'last_login'),
            'classes': ('collapse',),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nome', 'role', 'password1', 'password2'),
        }),
    )


class AlunoInline(admin.TabularInline):
    model = Aluno
    extra = 0
    show_change_link = True
    fields = ('user', 'escola_dest', 'classe', 'mensalidade', 'ativo')
    readonly_fields = ('criado_em',)
    autocomplete_fields = ('user',)


@admin.register(Encarregado)
class EncarregadoAdmin(admin.ModelAdmin):
    list_display = ('user', 'nrBI', 'telefone', 'total_alunos', _badge_ativo)
    list_filter = ('ativo',)
    search_fields = ('user__nome', 'user__email', 'nrBI')
    readonly_fields = ('idade', 'criado_em', 'atualizado_em')
    autocomplete_fields = ('user',)
    inlines = [AlunoInline]

    fieldsets = (
        ('Utilizador', {
            'fields': ('user', 'ativo')
        }),
        ('Dados Pessoais', {
            'fields': ('data_nascimento', 'idade', 'nrBI', 'telefone', 'endereco')
        }),
        ('Auditoria', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Alunos')
    def total_alunos(self, obj):
        return obj.alunos.count()


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ('user', 'escola_dest', 'classe', 'encarregado', 'mensalidade', _badge_ativo)
    list_filter = ('ativo', 'escola_dest', 'classe')
    search_fields = ('user__nome', 'user__email', 'nrBI', 'escola_dest')
    readonly_fields = ('idade', 'criado_em', 'atualizado_em')
    autocomplete_fields = ('user', 'encarregado')

    fieldsets = (
        ('Utilizador', {
            'fields': ('user', 'encarregado', 'ativo')
        }),
        ('Dados Pessoais', {
            'fields': ('data_nascimento', 'idade', 'nrBI', 'telefone', 'endereco')
        }),
        ('Dados Escolares', {
            'fields': ('escola_dest', 'classe', 'mensalidade')
        }),
        ('Auditoria', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Motorista)
class MotoristaAdmin(admin.ModelAdmin):
    list_display = ('user', 'carta_conducao', 'validade_da_carta', 'carta_status', 'salario', _badge_ativo)
    list_filter = ('ativo',)
    search_fields = ('user__nome', 'user__email', 'carta_conducao', 'nrBI')
    readonly_fields = ('idade', 'criado_em', 'atualizado_em', 'carta_status')
    autocomplete_fields = ('user',)

    fieldsets = (
        ('Utilizador', {
            'fields': ('user', 'ativo')
        }),
        ('Dados Pessoais', {
            'fields': ('data_nascimento', 'idade', 'nrBI', 'telefone', 'endereco')
        }),
        ('Carta de Condução', {
            'fields': ('carta_conducao', 'validade_da_carta', 'carta_status')
        }),
        ('Financeiro', {
            'fields': ('salario',)
        }),
        ('Auditoria', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Carta')
    def carta_status(self, obj):
        if obj.carta_conducao_vencida():
            return format_html('<span style="color:#dc2626;font-weight:600;">● Vencida</span>')
        return format_html('<span style="color:#16a34a;font-weight:600;">● Válida</span>')


@admin.register(Gestor)
class GestorAdmin(admin.ModelAdmin):
    list_display = ('user', 'departamento', 'salario', 'total_supervisionados', _badge_ativo)
    list_filter = ('ativo', 'departamento')
    search_fields = ('user__nome', 'user__email', 'nrBI')
    readonly_fields = ('idade', 'criado_em', 'atualizado_em')
    autocomplete_fields = ('user',)
    filter_horizontal = ('motoristas_supervisionados',)

    fieldsets = (
        ('Utilizador', {
            'fields': ('user', 'departamento', 'ativo')
        }),
        ('Dados Pessoais', {
            'fields': ('data_nascimento', 'idade', 'nrBI', 'telefone', 'endereco')
        }),
        ('Financeiro', {
            'fields': ('salario',)
        }),
        ('Supervisão', {
            'fields': ('motoristas_supervisionados',),
            'classes': ('collapse',),
        }),
        ('Auditoria', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Supervisionados')
    def total_supervisionados(self, obj):
        return obj.motoristas_supervisionados.count()


@admin.register(Monitor)
class MonitorAdmin(admin.ModelAdmin):
    list_display = ('user', 'salario', 'rota_ativa_display', _badge_ativo)
    list_filter = ('ativo',)
    search_fields = ('user__nome', 'user__email', 'nrBI')
    readonly_fields = ('idade', 'criado_em', 'atualizado_em', 'rota_ativa_display')
    autocomplete_fields = ('user',)

    fieldsets = (
        ('Utilizador', {
            'fields': ('user', 'ativo')
        }),
        ('Dados Pessoais', {
            'fields': ('data_nascimento', 'idade', 'nrBI', 'telefone', 'endereco')
        }),
        ('Financeiro', {
            'fields': ('salario',)
        }),
        ('Rota Actual', {
            'fields': ('rota_ativa_display',)
        }),
        ('Auditoria', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Rota Activa')
    def rota_ativa_display(self, obj):
        rota = obj.rota_ativa
        if rota:
            return format_html('<a href="/admin/transporte/rota/{}/change/">{}</a>', rota.pk, rota)
        return '—'
