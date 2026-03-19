"""
transporte/serializers.py
Serializers DRF para o módulo transporte.
"""

from rest_framework import serializers
from core.serializers import MotoristaListSerializer
from transporte.models import Abastecimento, Manutencao, Rota, TransporteAluno, Veiculo


class VeiculoListSerializer(serializers.ModelSerializer):
    """
    Versão leve para listagens.
    Inclui motorista nome, vagas disponíveis e indicadores críticos.
    """

    motorista_nome = serializers.CharField(
        source='motorista.user.nome', read_only=True, default=None
    )
    vagas_disponiveis = serializers.IntegerField(read_only=True)
    em_manutencao = serializers.BooleanField(read_only=True)
    precisa_manutencao = serializers.BooleanField(read_only=True)
    doc_em_dia = serializers.BooleanField(source='document_em_dia', read_only=True)

    class Meta:
        model = Veiculo
        fields = (
            'id', 'matricula', 'marca', 'modelo',
            'capacidade', 'vagas_disponiveis',
            'motorista_nome',
            'em_manutencao', 'precisa_manutencao', 'doc_em_dia',
            'ativo',
        )


class VeiculoSerializer(serializers.ModelSerializer):
    """Detalhe completo de um veículo com todos os indicadores calculados."""

    motorista = MotoristaListSerializer(read_only=True)
    vagas_disponiveis = serializers.IntegerField(read_only=True)
    custo_total_combustivel = serializers.FloatField(read_only=True)
    autonomia_estimada = serializers.FloatField(read_only=True)
    consumo_medio_km_l = serializers.SerializerMethodField()
    custo_por_km_mzn = serializers.SerializerMethodField()
    em_manutencao = serializers.BooleanField(read_only=True)
    precisa_manutencao = serializers.BooleanField(read_only=True)
    doc_em_dia = serializers.BooleanField(source='document_em_dia', read_only=True)
    alunos_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Veiculo
        fields = (
            'id', 'matricula', 'marca', 'modelo',
            'capacidade', 'capacidade_tanque',
            'motorista',
            'quilometragem_atual', 'data_ultima_revisao', 'km_proxima_revisao',
            'data_validade_seguro', 'data_validade_inspecao',
            'nr_manifesto', 'data_validade_manifesto',
            'vagas_disponiveis', 'alunos_count',
            'custo_total_combustivel', 'autonomia_estimada',
            'consumo_medio_km_l', 'custo_por_km_mzn',
            'em_manutencao', 'precisa_manutencao', 'doc_em_dia',
            'ativo', 'criado_em', 'atualizado_em',
        )
        read_only_fields = fields

    def get_consumo_medio_km_l(self, obj):
        v = obj.consumo_medio()
        return round(v, 2) if v else None

    def get_custo_por_km_mzn(self, obj):
        v = obj.custo_por_quilometro()
        return round(v, 2) if v else None


class VeiculoWriteSerializer(serializers.ModelSerializer):
    """Criação e edição de veículo."""

    class Meta:
        model = Veiculo
        fields = (
            'marca', 'modelo', 'matricula',
            'capacidade', 'capacidade_tanque', 'motorista', 'quilometragem_atual', 'data_ultima_revisao', 'km_proxima_revisao', 'data_validade_seguro', 'data_validade_inspecao',
            'nr_manifesto', 'data_validade_manifesto', 'ativo',
        )

    def validate_motorista(self, value):
        if value and not value.ativo:
            raise serializers.ValidationError('O motorista seleccionado está inactivo.')
        return value

    def validate(self, data):
        # Validação de conflito de motorista (respeita a instância em edição)
        motorista = data.get('motorista', getattr(self.instance, 'motorista', None))
        ativo = data.get('ativo', getattr(self.instance, 'ativo', True))
        pk = self.instance.pk if self.instance else None

        if motorista and ativo:
            conflito = Veiculo.objects.filter(
                motorista=motorista, ativo=True
            ).exclude(pk=pk)
            if conflito.exists():
                raise serializers.ValidationError({
                    'motorista': (
                        f'O motorista já está alocado ao veículo {conflito.first().matricula}.'
                    )
                })
        return data


class RotaSerializer(serializers.ModelSerializer):
    """Detalhe completo de uma rota."""

    veiculo_matricula = serializers.CharField(source='veiculo.matricula', read_only=True)
    motorista_nome = serializers.CharField(
        source='veiculo.motorista.user.nome', read_only=True, default=None
    )
    total_inscritos = serializers.IntegerField(read_only=True)
    vagas_disponiveis = serializers.IntegerField(
        source='veiculo.vagas_disponiveis', read_only=True
    )
    embarcados_hoje = serializers.SerializerMethodField()

    class Meta:
        model = Rota
        fields = (
            'id', 'nome', 'descricao',
            'veiculo', 'veiculo_matricula', 'motorista_nome', 'hora_partida', 'hora_chegada',
            'total_inscritos', 'vagas_disponiveis', 'embarcados_hoje', 'ativo', 'criado_em', 'atualizado_em',
        )

    def get_embarcados_hoje(self, obj):
        return obj.alunos_embarcados_hoje.count()


class RotaWriteSerializer(serializers.ModelSerializer):
    """Criação/edição de Rota."""

    class Meta:
        model = Rota
        fields = (
            'nome', 'descricao', 'veiculo', 'hora_partida', 'hora_chegada', 'ativo',
        )

    def validate_veiculo(self, value):
        if not value.ativo:
            raise serializers.ValidationError('O veículo está inactivo.')
        if not value.motorista:
            raise serializers.ValidationError('O veículo não tem motorista atribuído.')
        if value.em_manutencao():
            raise serializers.ValidationError('O veículo está em manutenção.')
        if not value.document_em_dia():
            raise serializers.ValidationError('O veículo tem documentação vencida.')
        if value.motorista.carta_conducao_vencida():
            raise serializers.ValidationError('O motorista tem carta de condução vencida.')
        return value

    def validate(self, data):
        hora_partida = data.get('hora_partida', getattr(self.instance, 'hora_partida', None))
        hora_chegada = data.get('hora_chegada', getattr(self.instance, 'hora_chegada', None))
        veiculo = data.get('veiculo', getattr(self.instance, 'veiculo', None))
        ativo = data.get('ativo', getattr(self.instance, 'ativo', True))
        pk = self.instance.pk if self.instance else None

        if hora_partida and hora_chegada and hora_chegada <= hora_partida:
            raise serializers.ValidationError({
                'hora_chegada': 'A hora de chegada deve ser posterior à partida.'
            })

        if veiculo and ativo:
            for outra in Rota.objects.filter(veiculo=veiculo, ativo=True).exclude(pk=pk):
                if hora_partida < outra.hora_chegada and hora_chegada > outra.hora_partida:
                    raise serializers.ValidationError({
                        'hora_partida': (
                            f"Conflito de turno com a rota '{outra.nome}' "
                            f"({outra.hora_partida}–{outra.hora_chegada})."
                        )
                    })
        return data


class TransporteAlunoSerializer(serializers.ModelSerializer):
    """Leitura do registo diário de transporte."""

    aluno_nome = serializers.CharField(source='aluno.user.nome', read_only=True)
    rota_nome = serializers.CharField(source='rota.nome', read_only=True)
    veiculo_matricula = serializers.CharField(
        source='rota.veiculo.matricula', read_only=True
    )

    class Meta:
        model = TransporteAluno
        fields = (
            'id', 'aluno', 'aluno_nome', 'rota', 'rota_nome', 'veiculo_matricula', 'status', 'data',
        )
        read_only_fields = ('data',)


class CheckInSerializer(serializers.ModelSerializer):
    """
    Actualização de status pelo motorista/monitor.
    Apenas o campo `status` é editável via este serializer.
    Inclui campos de leitura para contexto no dashboard.
    """

    aluno_nome = serializers.CharField(source='aluno.user.nome', read_only=True)
    rota_nome = serializers.CharField(source='rota.nome', read_only=True)
    veiculo_matricula = serializers.CharField(
        source='rota.veiculo.matricula', read_only=True
    )

    class Meta:
        model = TransporteAluno
        fields = (
            'id', 'aluno', 'aluno_nome',
            'rota', 'rota_nome', 'veiculo_matricula', 'status', 'data',
        )
        read_only_fields = ('aluno', 'rota', 'data')

    def validate_status(self, value):
        instance = self.instance
        if not instance:
            return value

        # Transições válidas: PENDENTE → EMBARCADO → DESEMBARCADO
        TRANSICOES = {
            'PENDENTE': ['EMBARCADO'],
            'EMBARCADO': ['DESEMBARCADO'],
            'DESEMBARCADO': [],
        }
        permitidas = TRANSICOES.get(instance.status, [])
        if value != instance.status and value not in permitidas:
            raise serializers.ValidationError(
                f"Transição inválida: {instance.status} → {value}. "
                f"Permitido: {permitidas or 'nenhuma'}."
            )
        return value


class ManutencaoSerializer(serializers.ModelSerializer):
    """Leitura e criação de manutenções."""

    veiculo_matricula = serializers.CharField(source='veiculo.matricula', read_only=True)

    class Meta:
        model = Manutencao
        fields = (
            'id', 'veiculo', 'veiculo_matricula',
            'tipo', 'descricao',
            'data_inicio', 'data_fim',
            'quilometragem_no_momento_revisao', 'km_proxima_revisao',
            'custo', 'concluida',
        )
        read_only_fields = ('data_fim', 'concluida')

    def validate(self, data):
        veiculo = data.get('veiculo', getattr(self.instance, 'veiculo', None))
        data_fim = data.get('data_fim', getattr(self.instance, 'data_fim', None))
        data_ini = data.get('data_inicio', getattr(self.instance, 'data_inicio', None))
        km_revisao = data.get(
            'quilometragem_no_momento_revisao',
            getattr(self.instance, 'quilometragem_no_momento_revisao', 0)
        )

        if data_fim and data_ini and data_fim < data_ini:
            raise serializers.ValidationError({
                'data_fim': 'A data de fim deve ser posterior à de início.'
            })
        if veiculo and km_revisao > veiculo.quilometragem_atual:
            raise serializers.ValidationError({
                'quilometragem_no_momento_revisao': (
                    f"Não pode exceder a quilometragem actual do veículo "
                    f"({veiculo.quilometragem_atual} km)."
                )
            })
        return data


class ManutencaoConcluirSerializer(serializers.Serializer):
    """Payload para a action /concluir de uma manutenção."""
    km_proximo_ajuste = serializers.IntegerField(
        default=7000, min_value=1000,
        help_text="Quilómetros até à próxima revisão (default: 7000)"
    )


class AbastecimentoSerializer(serializers.ModelSerializer):
    """Leitura e criação de abastecimentos."""

    veiculo_matricula = serializers.CharField(source='veiculo.matricula', read_only=True)
    custo_por_litro = serializers.SerializerMethodField()

    class Meta:
        model = Abastecimento
        fields = (
            'id', 'veiculo', 'veiculo_matricula', 'data', 'quilometragem_no_ato',
            'quantidade_litros', 'custo_total', 'custo_por_litro', 'posto_combustivel',
        )

    def get_custo_por_litro(self, obj):
        if obj.quantidade_litros and obj.quantidade_litros > 0:
            return round(float(obj.custo_total) / float(obj.quantidade_litros), 2)
        return None

    def validate(self, data):
        veiculo = data.get('veiculo', getattr(self.instance, 'veiculo', None))
        km_no_ato = data.get(
            'quilometragem_no_ato',
            getattr(self.instance, 'quilometragem_no_ato', 0)
        )
        if veiculo and km_no_ato < veiculo.quilometragem_atual:
            raise serializers.ValidationError({
                'quilometragem_no_ato': (
                    f"Não pode ser inferior à quilometragem actual do veículo "
                    f"({veiculo.quilometragem_atual} km)."
                )
            })
        return data
