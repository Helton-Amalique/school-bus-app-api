from django import forms
from transporte.models import Rota
from django.core.exceptions import ValidationError

class RotaForm(forms.ModelForm):
    """Form para criar ou editar uma rota.
    Tem validacao cruzada para impedir que se altere a rota se ela ja estiver em curso hje
    """
    class Meta:
        model = Rota
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        veiculo = cleaned_data.get('veiculo')
        alunos = cleaned_data.get('alunos')
        hora_partida = cleaned_data.get('hora_partida')
        hora_chegada = cleaned_data.get('hora_chegada')

        if hora_partida and hora_chegada and hora_chegada <= hora_partida:
            self.add_error(
                'hora_chegada',
                "A hora de chegada deve ser posterior à hora de partida."
            )

        if veiculo and alunos is not None:
            total = alunos.count()
            if total > veiculo.capacidade:
                self.add_error(
                    'alunos',
                    f"Capacidade excedida! O veículo {veiculo} só suporta "
                    f"{veiculo.capacidade} alunos, mas selecionou {total}."
                )
        return cleaned_data
