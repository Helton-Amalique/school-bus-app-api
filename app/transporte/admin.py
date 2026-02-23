from django.contrib import admin
from django.utils.html import format_html
from django import forms
from datetime import date
from core.models import Motorista
from django.core.exceptions import ValidationError
from transporte.models import Veiculo, Rota, TransporteAluno
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

            # if hasattr(self.instance, 'veiculo') and self.instance.veiculo:
            #     capacidade = self.instance.veiculo.capacidade
            #     if total_alunos > capacidade:
                    # raise ValidationError(f"Capacidade excedida! O veiculo {self.instance.veiculo} so suporta {capacidade} alunos, mas tentou inserir {total_alunos}.")


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ("matricula", "modelo", "marca", "motorista", "capacidade", "ativo", "vagas_disponiveis")
    list_filter = ("ativo", "motorista")
    search_fields = ("matricula", "modelo", "marca", "motorista__user__nome")
    readonly_fields = ("vagas_disponiveis", "criado_em", "atualizado_em")
    ordering = ("matricula",)


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
