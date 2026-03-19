from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from django.utils.html import format_html
# from django.utils import timezone
# from django.contrib.auth.models import Group
from core.models import User, Aluno, Encarregado, Motorista, Gestor, Monitor
# import datetime



class RoleFilter(admin.SimpleListFilter):
    title = 'Role'
    parameter_name = 'role'

    def lookups(self, request, model_admin):
        return User.Cargo.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(role=self.value())


class IdadeFilter(admin.SimpleListFilter):
    title = 'Faixa etária'
    parameter_name = 'faixa_etaria'

    def lookups(self, request, model_admin):
        return (
            ('menor', 'Menos de 18 anos'),
            ('adulto', '18 a 60 anos'),
            ('senior', 'Mais de 60 anos'),
        )

    def queryset(self, request, queryset):
        hoje = datetime.date.today()
        if self.value() == 'menor':
            return queryset.filter(data_nascimento__gt=hoje.replace(year=hoje.year - 18))
        if self.value() == 'adulto':
            return queryset.filter(
                data_nascimento__lte=hoje.replace(year=hoje.year - 18),
                data_nascimento__gt=hoje.replace(year=hoje.year - 60),
            )
        if self.value() == 'senior':
            return queryset.filter(data_nascimento__lte=hoje.replace(year=hoje.year - 60))


class CartaVencidaFilter(admin.SimpleListFilter):
    title = 'Carta de Condução'
    parameter_name = 'carta'

    def lookups(self, request, model_admin):
        return (
            ('valida', 'Válida'),
            ('vencida', 'Vencida'),
            ('sem_data', 'Sem data definida'),
        )

    def queryset(self, request, queryset):
        hoje = datetime.date.today()
        if self.value() == 'valida':
            return queryset.filter(validade_da_carta__gte=hoje)
        if self.value() == 'vencida':
            return queryset.filter(validade_da_carta__lt=hoje)
        if self.value() == 'sem_data':
            return queryset.filter(validade_da_carta__isnull=True)


class AlunoInline(admin.StackedInline):
    model = Aluno
    extra = 0
    fields = ('escola_dest', 'classe', 'mensalidade', 'ativo')
    show_change_link = True
    verbose_name = "Perfil de Aluno"


class EncarregadoInline(admin.StackedInline):
    model = Encarregado
    extra = 0
    fields = ('nrBI', 'telefone', 'endereco', 'ativo')
    show_change_link = True
    verbose_name = "Perfil de Encarregado"


class MotoristaInline(admin.StackedInline):
    model = Motorista
    extra = 0
    fields = ('nrBI', 'carta_conducao', 'validade_da_carta', 'salario', 'ativo')
    show_change_link = True
    verbose_name = "Perfil de Motorista"


class GestorInline(admin.StackedInline):
    model = Gestor
    extra = 0
    fields = ('nrBI', 'departamento', 'salario', 'ativo')
    show_change_link = True
    verbose_name = "Perfil de Gestor"


class MonitorInline(admin.StackedInline):
    model = Monitor
    extra = 0
    fields = ('nrBI', 'telefone', 'salario', 'ativo')
    show_change_link = True
    verbose_name = "Perfil de Monitor"


# @admin.register(User)
# class UserAdmin(BaseUserAdmin):
#     list_display = (
#         'email', 'nome', 'badge_role', 'is_active',
#         'is_staff', 'data_criacao',
#     )
#     list_filter = ('is_active', 'is_staff', RoleFilter)
#     search_fields = ('email', 'nome')
#     ordering = ('nome',)
#     readonly_fields = ('data_criacao', 'data_atualizacao', 'last_login')
#     list_per_page = 25

#     fieldsets = (
#         ('Credenciais', {
#             'fields': ('email', 'password')
#         }),
#         ('Informação Pessoal', {
#             'fields': ('nome', 'role')
#         }),
#         ('Permissões', {
#             'classes': ('collapse',),
#             'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
#         }),
#         ('Datas', {
#             'classes': ('collapse',),
#             'fields': ('data_criacao', 'data_atualizacao', 'last_login')
#         }),
#     )

#     add_fieldsets = (
#         ('Novo Utilizador', {
#             'classes': ('wide',),
#             'fields': ('email', 'nome', 'role', 'password1', 'password2', 'is_active', 'is_staff')
#         }),
#     )

#     # Inline dinâmico conforme o role do user
#     def get_inlines(self, request, obj=None):
#         if obj is None:
#             return []
#         mapa = {
#             'ALUNO':       [AlunoInline],
#             'ENCARREGADO': [EncarregadoInline],
#             'MOTORISTA':   [MotoristaInline],
#             'GESTOR':      [GestorInline],
#             'MONITOR':     [MonitorInline],
#         }
#         return mapa.get(obj.role, [])

#     @admin.display(description='Role')
#     def badge_role(self, obj):
#         cores = {
#             'ADMIN':       '#6f42c1',
#             'GESTOR':      '#0d6efd',
#             'MOTORISTA':   '#198754',
#             'MONITOR':     '#20c997',
#             'ENCARREGADO': '#fd7e14',
#             'ALUNO':       '#6c757d',
#         }
#         cor = cores.get(obj.role, '#343a40')
#         return format_html(
#             '<span style="background:{};color:white;padding:2px 8px;'
#             'border-radius:4px;font-size:11px">{}</span>',
#             cor, obj.get_role_display()
#         )

#     actions = ['ativar_users', 'desativar_users']

#     @admin.action(description='Ativar utilizadores selecionados')
#     def ativar_users(self, request, queryset):
#         updated = queryset.update(is_active=True)
#         self.message_user(request, f'{updated} utilizador(es) ativado(s).')

#     @admin.action(description='Desativar utilizadores selecionados')
#     def desativar_users(self, request, queryset):
#         updated = queryset.update(is_active=False)
#         self.message_user(request, f'{updated} utilizador(es) desativado(s).')


# @admin.register(Aluno)
# class AlunoAdmin(admin.ModelAdmin):
#     list_display = (
#         'user', 'escola_dest', 'classe',
#         'encarregado', 'mensalidade',
#         'badge_acesso', 'ativo',
#     )
#     list_filter = ('ativo', 'escola_dest', 'classe', IdadeFilter)
#     search_fields = ('user__nome', 'user__email', 'nrBI', 'escola_dest')
#     readonly_fields = ('criado_em', 'atualizado_em', 'idade_display')
#     list_per_page = 25
#     save_on_top = True

#     fieldsets = (
#         ('Utilizador', {
#             'fields': ('user', 'encarregado')
#         }),
#         ('Dados Pessoais', {
#             'fields': ('data_nascimento', 'idade_display', 'nrBI')
#         }),
#         ('Escola', {
#             'fields': ('escola_dest', 'classe')
#         }),
#         ('Financeiro', {
#             'fields': ('mensalidade', 'ativo')
#         }),
#         ('Datas do Sistema', {
#             'classes': ('collapse',),
#             'fields': ('criado_em', 'atualizado_em')
#         }),
#     )

#     @admin.display(description='Idade')
#     def idade_display(self, obj):
#         return f"{obj.idade} anos"

#     @admin.display(description='Acesso')
#     def badge_acesso(self, obj):
#         if obj.tem_acesso_bloqueado():
#             return format_html(
#                 '<span style="background:#dc3545;color:white;padding:2px 8px;'
#                 'border-radius:4px;font-size:11px">Bloqueado</span>'
#             )
#         return format_html(
#             '<span style="background:#198754;color:white;padding:2px 8px;'
#             'border-radius:4px;font-size:11px">Ativo</span>'
#         )

#     actions = ['ativar_alunos', 'desativar_alunos']

#     @admin.action(description='Ativar alunos selecionados')
#     def ativar_alunos(self, request, queryset):
#         queryset.update(ativo=True)
#         self.message_user(request, 'Alunos ativados.')

#     @admin.action(description='Desativar alunos selecionados')
#     def desativar_alunos(self, request, queryset):
#         queryset.update(ativo=False)
#         self.message_user(request, 'Alunos desativados.')


# class AlunosDoEncarregadoInline(admin.TabularInline):
#     model = Aluno
#     extra = 0
#     fields = ('user', 'escola_dest', 'classe', 'ativo')
#     readonly_fields = ('user',)
#     show_change_link = True
#     verbose_name = "Aluno"
#     verbose_name_plural = "Alunos do Encarregado"


# @admin.register(Encarregado)
# class EncarregadoAdmin(admin.ModelAdmin):
#     list_display = ('user', 'nrBI', 'telefone', 'total_alunos', 'ativo')
#     list_filter = ('ativo',)
#     search_fields = ('user__nome', 'user__email', 'nrBI')
#     readonly_fields = ('criado_em', 'atualizado_em')
#     list_per_page = 25
#     inlines = [AlunosDoEncarregadoInline]

#     fieldsets = (
#         ('Utilizador', {
#             'fields': ('user',)
#         }),
#         ('Dados Pessoais', {
#             'fields': ('nrBI', 'telefone', 'endereco', 'ativo')
#         }),
#         ('Datas do Sistema', {
#             'classes': ('collapse',),
#             'fields': ('criado_em', 'atualizado_em')
#         }),
#     )

#     @admin.display(description='Alunos')
#     def total_alunos(self, obj):
#         count = obj.alunos.count()
#         cor = '#198754' if count > 0 else '#6c757d'
#         return format_html(
#             '<span style="color:{};font-weight:bold">{}</span>', cor, count
#         )


# @admin.register(Motorista)
# class MotoristaAdmin(admin.ModelAdmin):
#     list_display = (
#         'user', 'carta_conducao',
#         'badge_carta', 'salario', 'ativo',
#     )
#     list_filter = ('ativo', CartaVencidaFilter)
#     search_fields = ('user__nome', 'user__email', 'nrBI', 'carta_conducao')
#     readonly_fields = ('criado_em', 'atualizado_em', 'idade_display')
#     list_per_page = 25
#     save_on_top = True

#     fieldsets = (
#         ('Utilizador', {
#             'fields': ('user',)
#         }),
#         ('Dados Pessoais', {
#             'fields': ('data_nascimento', 'idade_display', 'nrBI', 'telefone', 'endereco')
#         }),
#         ('Carta de Condução', {
#             'fields': ('carta_conducao', 'validade_da_carta', 'badge_carta')
#         }),
#         ('Financeiro', {
#             'fields': ('salario', 'ativo')
#         }),
#         ('Datas do Sistema', {
#             'classes': ('collapse',),
#             'fields': ('criado_em', 'atualizado_em')
#         }),
#     )

#     @admin.display(description='Idade')
#     def idade_display(self, obj):
#         return f"{obj.idade} anos"

#     @admin.display(description='Carta')
#     def badge_carta(self, obj):
#         if obj.carta_conducao_vencida():
#             return format_html(
#                 '<span style="background:#dc3545;color:white;padding:2px 8px;'
#                 'border-radius:4px;font-size:11px">Vencida</span>'
#             )
#         hoje = datetime.date.today()
#         if obj.validade_da_carta and (obj.validade_da_carta - hoje).days <= 30:
#             return format_html(
#                 '<span style="background:#fd7e14;color:white;padding:2px 8px;'
#                 'border-radius:4px;font-size:11px">Expira em breve</span>'
#             )
#         return format_html(
#             '<span style="background:#198754;color:white;padding:2px 8px;'
#             'border-radius:4px;font-size:11px">Válida</span>'
#         )


# @admin.register(Gestor)
# class GestorAdmin(admin.ModelAdmin):
#     list_display = (
#         'user', 'badge_departamento',
#         'total_motoristas', 'salario', 'ativo',
#     )
#     list_filter = ('ativo', 'departamento')
#     search_fields = ('user__nome', 'user__email', 'nrBI')
#     readonly_fields = ('criado_em', 'atualizado_em', 'idade_display')
#     filter_horizontal = ('motoristas_supervisionados',)
#     list_per_page = 25
#     save_on_top = True

#     fieldsets = (
#         ('Utilizador', {
#             'fields': ('user',)
#         }),
#         ('Dados Pessoais', {
#             'fields': ('data_nascimento', 'idade_display', 'nrBI', 'telefone', 'endereco')
#         }),
#         ('Função', {
#             'fields': ('departamento', 'salario', 'ativo')
#         }),
#         ('Supervisão', {
#             'fields': ('motoristas_supervisionados',)
#         }),
#         ('Datas do Sistema', {
#             'classes': ('collapse',),
#             'fields': ('criado_em', 'atualizado_em')
#         }),
#     )

#     @admin.display(description='Idade')
#     def idade_display(self, obj):
#         return f"{obj.idade} anos"

#     @admin.display(description='Departamento')
#     def badge_departamento(self, obj):
#         cores = {
#             'FROTA':      '#0d6efd',
#             'ACADEMICO':  '#6f42c1',
#             'FINANCEIRO': '#198754',
#             'GERAL':      '#6c757d',
#         }
#         cor = cores.get(obj.departamento, '#343a40')
#         return format_html(
#             '<span style="background:{};color:white;padding:2px 8px;'
#             'border-radius:4px;font-size:11px">{}</span>',
#             cor, obj.get_departamento_display()
#         )

#     @admin.display(description='Motoristas')
#     def total_motoristas(self, obj):
#         count = obj.motoristas_supervisionados.count()
#         return format_html(
#             '<span style="color:#0d6efd;font-weight:bold">{}</span>', count
#         )


# @admin.register(Monitor)
# class MonitorAdmin(admin.ModelAdmin):
#     list_display = (
#         'user', 'telefone',
#         'badge_rota', 'salario', 'ativo',
#     )
#     list_filter = ('ativo',)
#     search_fields = ('user__nome', 'user__email', 'nrBI')
#     readonly_fields = ('criado_em', 'atualizado_em', 'idade_display', 'badge_rota')
#     list_per_page = 25
#     save_on_top = True

#     fieldsets = (
#         ('Utilizador', {
#             'fields': ('user',)
#         }),
#         ('Dados Pessoais', {
#             'fields': ('data_nascimento', 'idade_display', 'nrBI', 'telefone', 'endereco')
#         }),
#         ('Estado', {
#             'fields': ('badge_rota', 'salario', 'ativo')
#         }),
#         ('Datas do Sistema', {
#             'classes': ('collapse',),
#             'fields': ('criado_em', 'atualizado_em')
#         }),
#     )

#     @admin.display(description='Idade')
#     def idade_display(self, obj):
#         return f"{obj.idade} anos"

#     @admin.display(description='Rota Ativa')
#     def badge_rota(self, obj):
#         rota = obj.rota_ativa
#         if rota:
#             return format_html(
#                 '<span style="background:#198754;color:white;padding:2px 8px;'
#                 'border-radius:4px;font-size:11px">{}</span>',
#                 rota.nome
#             )
#         return format_html(
#             '<span style="background:#6c757d;color:white;padding:2px 8px;'
#             'border-radius:4px;font-size:11px">Sem rota</span>'
#         )
