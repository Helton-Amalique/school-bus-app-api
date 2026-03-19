"""
transporte/urls.py"""

from rest_framework.routers import DefaultRouter

from transporte.views import (
    AbastecimentoViewSet,
    ManutencaoViewSet,
    RotaViewSet,
    TransporteAlunoViewSet,
    VeiculoViewSet,
)

app_name = 'transporte'

router = DefaultRouter()
router.register(r'veiculos', VeiculoViewSet, basename='veiculo')
router.register(r'rotas', RotaViewSet, basename='rota')
router.register(r'transportes', TransporteAlunoViewSet, basename='transporte')
router.register(r'manutencoes', ManutencaoViewSet, basename='manutencao')
router.register(r'abastecimentos', AbastecimentoViewSet, basename='abastecimento')

urlpatterns = router.urls
