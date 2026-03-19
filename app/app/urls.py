"""
config/urls.py
==============
URLs raiz do projecto — Sistema de Transporte Escolar.

Estrutura:
  /admin/                     → Django Admin
  /api/v1/                    → API REST (todos os módulos)
  /api/v1/auth/token/         → Obter par de tokens JWT (login)
  /api/v1/auth/token/refresh/ → Renovar access token
  /api/v1/auth/token/verify/  → Verificar validade de token
  /api/schema/                → OpenAPI 3 schema (drf-spectacular)
  /api/docs/                  → Swagger UI
  /api/redoc/                 → ReDoc UI

Dependências esperadas em INSTALLED_APPS:
  - rest_framework
  - rest_framework_simplejwt
  - drf_spectacular
  - django_filters
  - core
  - transporte
  - financeiro
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

try:
    from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView,)
    _SPECTACULAR = True
except ImportError:
    _SPECTACULAR = False


auth_patterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]

api_v1_patterns = [
    path('auth/', include((auth_patterns, 'auth'))),
    path('', include('core.urls', namespace='core')),
    path('', include('transporte.urls', namespace='transporte')),
    path('', include('financeiro.urls', namespace='financeiro')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include((api_v1_patterns, 'api_v1'))),
]

if _SPECTACULAR:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]
