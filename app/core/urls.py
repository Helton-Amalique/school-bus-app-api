"""
core/urls.py
"""
from rest_framework.routers import DefaultRouter
from core.views import (
    AlunoViewSet,
    EncarregadoViewSet,
    GestorViewSet,
    MonitorViewSet,
    MotoristaViewSet,
    UserViewSet,
)

app_name = 'core'

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'encarregados', EncarregadoViewSet, basename='encarregado')
router.register(r'alunos', AlunoViewSet, basename='aluno')
router.register(r'motoristas', MotoristaViewSet, basename='motorista')
router.register(r'gestores', GestorViewSet, basename='gestor')
router.register(r'monitores', MonitorViewSet, basename='monitor')

urlpatterns = router.urls
