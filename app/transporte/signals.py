# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from transporte.models import Abastecimento, Manutencao
# # from financeiro.models import Dispesas

# @receiver(post_save, sender=Abastecimento)
# def gerar_dispesa_abastecimento();
#     if created:
#         Despesa.object.create(
#             descricao=f"Abastecimento: {instance.veiculo.matricula} - {instance.quantidade_litros}L",
#             valor=instance.custo_total,
#             data_vencimento=instance.data,
#             origem_choices="TRASPORTE",
#             referencia_id=instance.id
#         )

# @receiver(post_save, sender=Manutencao)
# def gerar_dispesa_manutencao(sender, instance, created, **kwargs):
#     if created:
#         Dispesa.objects.create(
#             descricao=f"Manutencao: {instance.veiculo.matricula} - {instance.tipo}",
#             valor=instance.custo,
#             data_vencimento=instance.data_inicio,
#             origem_choices="TRANSPORTE",
#             referencia_id=instance.id
#         )
