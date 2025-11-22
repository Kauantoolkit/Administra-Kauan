from django.urls import path
from . import views

urlpatterns = [
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('clientes/', views.clientes_view, name='clientes'),
    path('estoque/', views.estoque_view, name='estoque'),
    path('estoque/entrada/', views.entrada_estoque_geral_view, name='entrada_estoque'),
    path('produtos/novo/', views.novo_produto_view, name='novo_produto'),
    path('produtos/<int:pk>/detalhe/', views.detalhe_produto_view, name='detalhe_produto'),
    path('produtos/<int:pk>/editar/', views.editar_produto_view, name='editar_produto'),
    path('produtos/<int:pk>/adicionar-estoque/', views.adicionar_estoque_view, name='entrada_produto'),
    path('produtos/<int:pk>/excluir/', views.excluir_produto_view, name='excluir_produto'),
    path("estoque/detalhes/<int:pk>/", views.detalhes_produto_ajax, name="detalhes_produto_ajax"),

    
]