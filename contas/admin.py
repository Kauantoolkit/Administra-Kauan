from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import (
    Categoria, ConfiguracaoLoja, CustomUser, Fornecedor, MovimentoEstoque,
    Produto, ProdutoVariacao,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ('email', 'nome', 'papel', 'is_staff', 'is_active')
    list_filter = ('papel', 'is_staff', 'is_active')
    search_fields = ('email', 'nome', 'cpf')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Dados pessoais', {'fields': ('nome', 'cpf', 'papel')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                   'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nome', 'cpf', 'papel', 'password1', 'password2'),
        }),
    )


class ProdutoVariacaoInline(admin.TabularInline):
    model = ProdutoVariacao
    extra = 1
    readonly_fields = ('quantidade_estoque',)


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sku', 'unidade_medida', 'venda',
                    'estoque_formatado', 'status', 'ativo')
    list_filter = ('unidade_medida', 'status', 'ativo', 'categoria', 'controla_estoque')
    search_fields = ('nome', 'sku', 'codigo_barras', 'marca')
    readonly_fields = ('quantidade_estoque', 'status')
    inlines = [ProdutoVariacaoInline]


@admin.register(MovimentoEstoque)
class MovimentoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('produto', 'tipo_movimento', 'quantidade', 'data_movimento', 'usuario')
    list_filter = ('tipo_movimento', 'data_movimento')
    search_fields = ('produto__nome', 'produto__sku', 'observacao')
    autocomplete_fields = ('produto',)


@admin.register(ConfiguracaoLoja)
class ConfiguracaoLojaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ConfiguracaoLoja.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Categoria)
admin.site.register(Fornecedor)
admin.site.site_header = 'Administra — Administração'
admin.site.site_title = 'Administra'
