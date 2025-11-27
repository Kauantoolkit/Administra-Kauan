
from django.urls import path
from . import views

urlpatterns = [
    path('', views.funcionarios_list, name='funcionarios_list'),
    path('novo/', views.funcionario_create, name='funcionario_create'),
    path('editar/<int:pk>/', views.funcionario_edit, name='funcionario_edit'),
    path("funcionarios/<int:pk>/", views.funcionario_detail, name="funcionario_detail"),
    path('deletar/<int:pk>/', views.funcionario_delete, name='funcionario_delete'),
]
