"""
app/celery.py
=============
Configuração central do Celery para o Sistema de Transporte Escolar.
"""

import os

from celery import Celery
from celery.schedules import crontab

# Definir o settings por omissão para o programa celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

app = Celery('app')

# Ler configuração a partir das settings Django com prefixo CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobrir tasks automaticamente em todas as apps instaladas
app.autodiscover_tasks()


# ── Agenda de tarefas periódicas (Celery Beat) ────────────────────────────────

app.conf.beat_schedule = {

    # ── Financeiro ─────────────────────────────────────────────────────────────

    'gerar-mensalidades-todo-mes': {
        'task': 'financeiro.tasks.gerar_mensalidades_mes',
        # Dia 1 de cada mês às 07:00
        'schedule': crontab(hour=7, minute=0, day_of_month=1),
    },

    'aplicar-multas-diario': {
        'task': 'financeiro.tasks.aplicar_multas_automaticas',
        # Todos os dias 11 de cada mes às 07:00
        'schedule': crontab(hour=7, minute=0, day_of_month=11),
    },

    'notificar-mensalidades-atraso-diario': {
        'task': 'financeiro.tasks.notificar_mensalidades_atraso',
        # Todzs as segundas feiras às 09:00
        'schedule': crontab(hour=9, minute=0, day_of_week=1),
    },

    'notificar-mensalidades-a-vencer-diario': {
        'task': 'financeiro.tasks.notificar_mensalidades_a_vencer',
        # Todos os dias às 09:30
        'schedule': crontab(hour=9, minute=30),
    },

    'notificar-folhas-pendentes-semanal': {
        'task': 'financeiro.tasks.notificar_folhas_pendentes',
        # Todas as segundas-feiras às 08:00
        'schedule': crontab(hour=8, minute=0, day_of_week=1),
    },

    # ── Transporte ─────────────────────────────────────────────────────────────

    'notificar-cartas-conducao-semanal': {
        'task': 'transporte.tasks.notificar_cartas_conducao',
        # Todas as segundas-feiras às 08:30
        'schedule': crontab(hour=8, minute=30, day_of_week=1),
    },

    'notificar-documentos-veiculo-semanal': {
        'task': 'transporte.tasks.notificar_documentos_veiculo',
        # Todas as terças-feiras às 08:00
        'schedule': crontab(hour=8, minute=0, day_of_week=2),
    },

    'notificar-revisao-veiculo-semanal': {
        'task': 'transporte.tasks.notificar_revisao_veiculo',
        # Todas as terças-feiras às 08:30
        'schedule': crontab(hour=8, minute=30, day_of_week=2),
    },
}

app.conf.timezone = 'Africa/Maputo'
