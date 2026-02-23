from django.contrib import admin
from django.utils.html import format_html
from datetime import date
from core.models import Motorista
from transporte.models import Veiculo, Rota, TransporteAluno


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ("matricula", "modelo", "marca", "motorista", "capacidade", "ativo", "vagas_disponiveis")
    list_filter = ("ativo", "motorista")
    search_fields = ("matricula", "modelo", "marca", "motorista__user__nome")
    readonly_fields = ("vagas_disponiveis", "criado_em", "atualizado_em")
    ordering = ("matricula",)


class AlunoInline(admin.TabularInline):
    model = Rota.alunos.through
    extra = 1
    verbose_name = "Aluno na Rota"

@admin.register(Rota)
class RotaAdmin(admin.ModelAdmin):

    list_display = ("nome", "veiculo", "motorista", "ativo", "criado_em")
    inlines = [AlunoInline]
    list_filter = ("ativo", "veiculo__marca")
    search_fields = ("nome", "veiculo__matricula")
    ordering = ("nome",)


@admin.register(TransporteAluno)
class TransporteAlunoAdmin(admin.ModelAdmin):
    list_display = ("aluno", "rota", "status", "data")
    readonly_fields = ("data",)
    list_filter = ("status", "rota", "data")
    search_fields = ("aluno__user__email", "aluno_user_email", "rota__nome")
    date_hierarchy = "data"

@admin.display(description="Status Visual")
def data_badge(self, obj):
    cores = {"PENDENTE": "orange", "EMBARCADO": "green", "DESEMBARCADO": "blue"}
    return format_html(
        '<strong style="color: {};">{}</strong>',
        cores.get(obj.status, "black"),
        obj.status
    )
