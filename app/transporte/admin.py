from django.contrib import admin
from django.utils.html import format_html
from django import forms
from datetime import date
from core.models import Motorista
from django.core.exceptions import ValidationError
from transporte.models import Veiculo, Rota, TransporteAluno, Manutencao
from transporte.forms import RotaForm

class AlunoRotaFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()

        total_alunos = 0
        for form in self.forms:
            if form.is_valid() and form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                total_alunos += 1

        veiculo = getattr(self.instance, 'veiculo', None)
        if veiculo:
            capacidade = veiculo.capacidade
            if total_alunos > capacidade:
                raise ValidationError(f"Capacidade excedida! O veiculo {veiculo} so suporta {capacidade} alunos, mas tentou inserir {total_alunos}.")

class ManutencaoInline(admin.TabularInline):
    model = Manutencao
    extra = 1
    fields = ("get_matricula", "get_marca", "get_modelo", "data_inicio", "data_fim", "descricao", "custo", "concluida")
    readonly_fields = ("get_matricula", "get_marca", "get_modelo")
    verbose_name = "Manutenção do Veiculo"
    verbose_name_plural = "Manutenções do Veiculo"

    @admin.display(description="Matrícula")
    def get_matricula(self, obj):
        return obj.veiculo.matricula

    @admin.display(description="Marca")
    def get_marca(self, obj):
        return obj.veiculo.marca

    @admin.display(description="Modelo")
    def get_modelo(self, obj):
        return obj.veiculo.modelo

@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ("matricula", "modelo", "marca", "motorista", "capacidade", "ativo", "vagas_disponiveis")
    list_filter = ("ativo", "motorista")
    search_fields = ("matricula", "modelo", "marca", "motorista__user__nome")
    inlines = [ManutencaoInline]
    readonly_fields = ("status_visual", "vagas_disponiveis", "criado_em", "atualizado_em")
    ordering = ("matricula",)

    fieldsets = (
        ("Informação Básica", {"fields": ("marca", "modelo", "matricula", "capacidade", "motorista")}),
        ("Estado e Logística", {"fields": ("ativo", "vagas_disponiveis")}),
        ("Manutenção Preventiva", {
            "fields": ("quilometragem_atual", "km_proxima_revisao", "data_ultima_revisao", "status_visual"),
            "description": "Controle de KMs para evitar paragens inesperadas."
        }),)

    @admin.display(description="Status Visual")
    def status_visual(self, obj):
        if obj.quilometragem_atual >= (obj.km_proxima_revisao - 500):
            return "Necessita Revisão"
        return "OPERACIONAL"

class AlunoInline(admin.TabularInline):
    model = Rota.alunos.through
    formset = AlunoRotaFormSet
    extra = 1
    verbose_name = "Aluno na Rota"
    verbose_name_plural = "Alunos na Rota"

@admin.register(Rota)
class RotaAdmin(admin.ModelAdmin):

    form = RotaForm
    list_display = ("nome", "veiculo", "motorista", "get_lotacao", "ativo", "criado_em")
    inlines = [AlunoInline]
    exclude = ("alunos",)
    list_filter = ("ativo", "veiculo__marca")
    search_fields = ("nome", "veiculo__matricula")
    ordering = ("nome",)

    def get_lotacao(self, obj):
        return f"{obj.alunos.count()} / {obj.veiculo.capacidade}"
    get_lotacao.short_description = "Lotação"


@admin.register(TransporteAluno)
class TransporteAlunoAdmin(admin.ModelAdmin):
    list_display = ("aluno", "rota", "status", "data")
    readonly_fields = ("data",)
    list_filter = ("status", "rota", "data")
    search_fields = ("aluno__user__email", "rota", "rota__nome")
    date_hierarchy = "data"

@admin.display(description="Status Visual")
def data_badge(self, obj):
    cores = {"PENDENTE": "orange", "EMBARCADO": "green", "DESEMBARCADO": "blue"}
    return format_html(
        '<strong style="color: {};">{}</strong>',
        cores.get(obj.status, "black"),
        obj.status
    )
