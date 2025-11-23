from django.urls import path
from . import views

urlpatterns = [
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('clientes/', views.clientes_view, name='clientes'),
    path('relatorios/', views.relatorios, name='relatorios'),
    path('fornecedores/', views.fornecedores_view, name='fornecedores'),
    path('fornecedores/criar/', views.fornecedor_criar, name='fornecedor_criar'),
    path('fornecedores/<int:pk>/editar/', views.fornecedor_editar, name='fornecedor_editar'),
    path('fornecedores/<int:pk>/deletar/', views.fornecedor_deletar, name='fornecedor_deletar'),
    path('estoque/', views.estoque_view, name='estoque'),
    path('estoque/entrada/', views.entrada_estoque_geral_view, name='entrada_estoque'),
    path('produtos/novo/', views.novo_produto_view, name='novo_produto'),
    path('produtos/<int:pk>/detalhe/', views.detalhe_produto_view, name='detalhe_produto'),
    path('produtos/<int:pk>/editar/', views.editar_produto_view, name='editar_produto'),
    path('produtos/<int:pk>/adicionar-estoque/', views.adicionar_estoque_view, name='entrada_produto'),
    path('produtos/<int:pk>/excluir/', views.excluir_produto_view, name='excluir_produto'),
    path("estoque/detalhes/<int:pk>/", views.detalhes_produto_ajax, name="detalhes_produto_ajax"),
    path('estoque/exportar/', views.exportar_estoque_csv, name='exportar_estoque'),
    path('estoque/imprimir-codigos/', views.imprimir_codigos_estoque, name='imprimir_codigos_estoque'),
]
