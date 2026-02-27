from django.urls import path, include
from rest_framework.routers import DefaultRouter
from transporte import views

app_name = "transportes"

router = DefaultRouter()

router.register(r'veiculos', views.VeiculoViewSet, basename='veiculo')
router.register(r'rotas', views.RotaViewSet, basename='rota')
router.register(r'check-in', views.TransportViewSet, basename='transporte-aluno')
router.register(r'manutencoes', views.ManutencaoViewSet, basename='manutencao')

urlpatterns = [
    path('', include(router.urls)),
]
