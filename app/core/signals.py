from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from accounts.models import Aluno, Encarregado, Motorista

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        if instance.role == 'ALUNO':
            Aluno.objects.create(user=instance)
        elif instance.role == 'ENCARREGADO':
            Encarregado.objects.create(user=instance)
        elif instance.role == 'MOTORISTA':
            Motorista.objects.create(user=instance)
