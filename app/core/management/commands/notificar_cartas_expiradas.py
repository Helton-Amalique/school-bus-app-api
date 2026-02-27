from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from transporte.models import Motorista
from datetime import timedelta


class Command(BaseCommand):
    help = 'Envia notificações para motoristas com carta de condução expirada ou prestes a expirar'

    def handle(self, *args, **options):
        hoje = timezone.now().date()
        proximos_30_dias = hoje + timedelta(days=30)

        motoristas_expirados = Motorista.objects.filter(validade_da_carta__lt=hoje)
        motoristas_proximos_expirar = Motorista.objects.filter(validade_da_carta__gte=hoje, validade_da_carta__lte=proximos_30_dias)

        for motorista in motoristas_expirados:
            send_mail(
                'Carta de Condução Expirada',
                f'Prezado {motorista.user.nome}, sua carta de condução expirou em {motorista.validade_da_carta}. Por favor, regularize sua situação o mais rápido possível.',
                'admin@schoolbus.com',  # Remetente padrão
                [motorista.user.email],  # Destinatário
                fail_silently=False,
            )
        for motorista in motoristas_proximos_expirar:
            send_mail(
                'Carta de Condução Próxima de Expirar',
                f'Prezado {motorista.user.nome}, sua carta de condução expira em {motorista.validade_da_carta}. Por favor, renove sua carta o mais rápido possível.',
                'admin@schoolbus.com',  # Remetente padrão
                [motorista.user.email],  # Destinatário
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'Notificação enviada para {motorista.user.email} sobre carta próxima de expirar.'))
        self.stdout.write(self.style.SUCCESS('Notificações enviadas para motoristas com carta expirada ou próxima de expirar.'))
