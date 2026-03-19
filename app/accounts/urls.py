# from django.urls import include, path
# from rest_framework.routers import DefaultRouter
# from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView, TokenVerifyView)
# from accounts.views import CreateUserView, CreateTokenView, ManageUserView

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core import views


app_name = 'accounts'

router = DefaultRouter()
# router.register(r"users", views.UserViewSet.as_view, basename="user")

# urlpatterns = [
#     path('create/', CreateUserView.as_view(), name='create_user'),
#     path('token/', CreateTokenView.as_view(), name='token'),
#     path('me/', ManageUserView.as_view(), name='me'),

#     # path("", include(router.urls)),
# ]


router.register(r'users', views.UserViewSet, basename='user')
router.register(r'alunos', views.AlunoViewSet, basename='aluno')
router.register(r'encarregados', views.EncarregadoViewSet, basename='encarregado')
router.register(r'motoristas', views.MotoristaViewSet, basename='motorista')
router.register(r'gestores', views.GestorViewSet, basename='gestor')
router.register(r'monitores', views.MonitorViewSet, basename='monitor')

urlpatterns = [
    path('', include(router.urls)),

    # ── User ──
    path(
        'users/me/',
        views.UserViewSet.as_view({'get': 'me'}),
        name='user-me',
    ),
    path(
        'users/alterar-password/',
        views.UserViewSet.as_view({'post': 'alterar_password'}),
        name='user-alterar-password',
    ),
    path(
        'users/<int:pk>/desativar/',
        views.UserViewSet.as_view({'post': 'desativar'}),
        name='user-desativar',
    ),

    # ── Perfis — me/ ──
    path(
        'alunos/me/',
        views.AlunoViewSet.as_view({'get': 'me'}),
        name='aluno-me',
    ),
    path(
        'motoristas/me/',
        views.MotoristaViewSet.as_view({'get': 'me'}),
        name='motorista-me',
    ),
    path(
        'gestores/me/',
        views.GestorViewSet.as_view({'get': 'me'}),
        name='gestor-me',
    ),
    path(
        'monitores/me/',
        views.MonitorViewSet.as_view({'get': 'me'}),
        name='monitor-me',
    ),
    path(
        'encarregados/me/',
        views.EncarregadoViewSet.as_view({'get': 'me'}),
        name='encarregado-me',
    ),

    # ── Aluno ──
    path(
        'alunos/<int:pk>/rotas/',
        views.AlunoViewSet.as_view({'get': 'rotas'}),
        name='aluno-rotas',
    ),
    path(
        'alunos/com-acesso-bloqueado/',
        views.AlunoViewSet.as_view({'get': 'com_acesso_bloqueado'}),
        name='aluno-acesso-bloqueado',
    ),

    # ── Encarregado ──
    path(
        'encarregados/<int:pk>/alunos/',
        views.EncarregadoViewSet.as_view({'get': 'alunos'}),
        name='encarregado-alunos',
    ),

    # ── Motorista ──
    path(
        'motoristas/carta-vencida/',
        views.MotoristaViewSet.as_view({'get': 'carta_vencida'}),
        name='motorista-carta-vencida',
    ),
    path(
        'motoristas/<int:pk>/veiculos/',
        views.MotoristaViewSet.as_view({'get': 'veiculos'}),
        name='motorista-veiculos',
    ),

    # ── Gestor ──
    path(
        'gestores/<int:pk>/adicionar-motorista/',
        views.GestorViewSet.as_view({'post': 'adicionar_motorista'}),
        name='gestor-adicionar-motorista',
    ),
    path(
        'gestores/<int:pk>/remover-motorista/',
        views.GestorViewSet.as_view({'post': 'remover_motorista'}),
        name='gestor-remover-motorista',
    ),

    # ── Monitor ──
    path(
        'monitores/sem-rota/',
        views.MonitorViewSet.as_view({'get': 'sem_rota'}),
        name='monitor-sem-rota',
    ),
    path(
        'monitores/<int:pk>/rota-atual/',
        views.MonitorViewSet.as_view({'get': 'rota_atual'}),
        name='monitor-rota-atual',
    ),
]
