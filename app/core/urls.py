from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import AlunoViewSet, EncarregadoViewSet, MotoristaViewSet

app_name='core'

router = DefaultRouter()
router.register(r'alunos', AlunoViewSet, basename='aluno')
router.register(r'encarregados', EncarregadoViewSet, basename='encarregado')
router.register(r'motoristas', MotoristaViewSet, basename='motorista')

urlpatterns = [
    path('', include(router.urls)),
]
