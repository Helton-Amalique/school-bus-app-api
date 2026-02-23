from rest_framework import serializers
from transporte.models import Veiculo, Rota, TransporteAluno
from core.serializers import AlunoSerializer
from django.utils import timezone

class VeiculoSerializer(serializers.ModelSerializer):
    """Mostra a saude do veiculo
    Inclui um badge de lotacao para front-end
    """

    motorista_nome = serializers.ReadOnlyField(source='motorista.user.nome')
    vagas_disponiveis = serializers.ReadOnlyField()
    estado_lotacao = serializers.SerializerMethodField()

    class Meta:
        model = Veiculo
        fields = '__all__'
        # fields = ['id', 'marca', 'modelo', 'matricula', 'capacidade', 'vagas_disponiveis', 'motorista_nome', 'estado_lotacao', 'ativo']

    def get_estado_lotacao(self, obj) -> str:
        vagas = obj.vagas_disponiveis
        if obj.capacidade == 0:
            return "erro capacidade. 0"
        perc =(vagas / obj.capacidade) * 100
        if perc == 0:
            return "Lotado"
        if perc < 20:
            return "Critico"
        return "OK"


class RotaSerializer(serializers.ModelSerializer):
    """Serializer com escrita inteligent
    Impede que se altere a rota  se ela ja estiver em curso hje
    """

    alunos_count = serializers.IntegerField(source='alunos.count', read_only=True)
    veiculo_info = serializers.StringRelatedField(source='veiculo', read_only=True)

    class Meta:
        model = Rota
        fields = '__all__'
        # fields = ['id', 'nome', 'veiculo_info', 'hora_partida', 'hora_chegada', 'alunos', 'aluno_count', 'ativo']

    def validate(self, data):
        """validacao cruzada: Capacidade vs Alunos"""
        veiculo = data.get('veiculo') or self.instance.veiculo
        alunos = data.get('alunos')

        if alunos and len(alunos) > veiculo.capacidade:
            raise serializers.ValidationError({"alunos": f"O veiculo {veiculo.matricula} so suporta {veiculo.capacidade} alunos. Tento inserir {len(alunos)}."})


class CheckInSerializer(serializers.ModelSerializer):
    """Serializer Otimizado para o Motorista (check via tablet).
    Apenas permite atualizar o status, o resto e Ready Only.
    """
    aluno_nome = serializers.ReadOnlyField(source='aluno.user.nome')
    foto_aluno = serializers.ImageField(source='aluno.foto', read_only=True)

    class Meta:
        model = TransporteAluno
        fields = '__all__'
        # fiellds = ['id', 'aluno_nome', 'foto_aluno', 'status', 'data']
        read_only_fields = ['aluno_nome', 'data']

    def validate_status(self, value):
        """Impede retrocesso de status (ex: de Desembarque para Pendente)"""
        if self.instance and self.instance.status == "DESEMBARCADO":
            raise serializers.ValidationError("Nao pode alterar o status")
        return value
