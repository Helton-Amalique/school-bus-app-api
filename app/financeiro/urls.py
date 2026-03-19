from rest_framework.routers import DefaultRouter

from financeiro.views import (
    BalancoMensalViewSet,
    CategoriaViewSet,
    ConfiguracaoFinanceiraViewSet,
    DespesaGeralViewSet,
    DespesaVeiculoViewSet,
    FolhaPagamentoViewSet,
    FuncionarioViewSet,
    MensalidadeViewSet,
    TransacaoViewSet,
)

app_name = 'financeiro'

router = DefaultRouter()
router.register(r'configuracao', ConfiguracaoFinanceiraViewSet, basename='configuracao')
router.register(r'categorias', CategoriaViewSet, basename='categoria')
router.register(r'transacoes', TransacaoViewSet, basename='transacao')
router.register(r'funcionarios', FuncionarioViewSet, basename='funcionario')
router.register(r'mensalidades', MensalidadeViewSet, basename='mensalidade')
router.register(r'folhas', FolhaPagamentoViewSet, basename='folha')
router.register(r'despesas-veiculo', DespesaVeiculoViewSet, basename='despesa-veiculo')
router.register(r'despesas-gerais', DespesaGeralViewSet, basename='despesa-geral')
router.register(r'balancos', BalancoMensalViewSet, basename='balanco')

urlpatterns = router.urls
