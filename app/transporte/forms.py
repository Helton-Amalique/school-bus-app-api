from django import forms
from django.core.exceptions import ValidationError
from transporte.models import Rota

class RotaForm(forms.ModelForm):
    """Form para criar ou editar uma rota.
    Tem validacao cruzada para impedir que se altere a rota se ela ja estiver em curso hje
    """

    class Meta:
        model = Rota
        fields = '__all__'
        # fields = ['nome', 'veiculo', 'hora_partida', 'hora_chegada', 'alunos', 'ativo']

    def clean(self):
        cleaned_data = super().clean()
        veiculo = cleaned_data.get('veiculo')
        alunos = cleaned_data.get('alunos')

        if veiculo and alunos:
            if alunos.count() > veiculo.capacidade:
                raise ValidationError(
                    f"Capacidade excedida! O veiculo {veiculo} so suporta"
                    f"{veiculo.capacidade} alunos, mas selecionou {alunos.count()}."
                )
        return cleaned_data

        # if hora_partida and hora_chegada and hora_partida >= hora_chegada:
        #     raise ValidationError("A hora de partida deve ser antes da hora de chegada.")