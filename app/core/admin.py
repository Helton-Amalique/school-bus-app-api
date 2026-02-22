from django.contrib import admin
from core.models import Aluno, Encarregado, Motorista


# Ações comuns
@admin.action(description="Marcar selecionados como ativos")
def marcar_ativos(modeladmin, request, queryset):
    queryset.update(ativo=True)

@admin.action(description="Marcar selecionados como inativos")
def marcar_inativos(modeladmin, request, queryset):
    queryset.update(ativo=False)

@admin.action(description="Exportar selecionados para CSV")
def exportar_csv(modeladmin, request, queryset):
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="export.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Nome', 'Email', 'Ativo'])

    for obj in queryset:
        writer.writerow([obj.id, obj.user.nome, obj.user.email, obj.ativo])

    return response


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "get_email", "encarregado", "escola_dest", "classe", "mensalidade", "idade", "ativo")
    search_fields = ("user__nome", "user__email", "classe", "nrBI")
    list_filter = ("ativo", "classe", "escola_dest")
    ordering = ("user__nome",)
    list_select_related = ("user", "encarregado")
    readonly_fields = ("criado_em", "atualizado_em")
    autocomplete_fields = ("user", "encarregado")
    actions = [marcar_ativos, marcar_inativos, exportar_csv]

    def get_email(self, obj):
        return obj.user.email if obj.user else "-"
    get_email.short_description = "Email do Aluno"
    get_email.admin_order_field = "user__email"

    def idade(self, obj):
        return obj.idade
    idade.short_description = "Idade"


@admin.register(Encarregado)
class EncarregadoAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "get_email", "telefone", "nrBI", "ativo")
    search_fields = ("user__nome", "user__email", "nrBI", "telefone")
    list_filter = ("ativo",)
    ordering = ("user__nome",)
    list_select_related = ("user",)
    actions = [marcar_ativos, marcar_inativos, exportar_csv]

    def get_email(self, obj):
        return obj.user.email if obj.user else "-"
    get_email.short_description = "Email"
    get_email.admin_order_field = "user__email"


@admin.register(Motorista)
class MotoristaAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "get_email", "nrBI", "carta_conducao", "telefone", "idade", "salario", "ativo")
    search_fields = ("user__nome", "user__email", "nrBI", "carta_conducao", "telefone")
    list_filter = ("ativo",)
    ordering = ("user__nome",)
    list_select_related = ("user",)
    actions = [marcar_ativos, marcar_inativos, exportar_csv]

    def get_email(self, obj):
        return obj.user.email if obj.user else "-"
    get_email.short_description = "Email"
    get_email.admin_order_field = "user__email"

    def idade(self, obj):
        return obj.idade
    idade.short_description = "Idade"
