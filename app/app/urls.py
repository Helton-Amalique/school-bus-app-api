from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

app_name ='accounts'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('api/core/', include(('core.urls', 'core'), namespace='core')),
    path('api/transportes/', include(('transporte.urls', 'transporte'), namespace='transporte')),


    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),

]
