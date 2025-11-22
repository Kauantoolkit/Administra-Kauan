from django.apps import AppConfig

class ContasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'contas'

    def ready(self):

        from django.db.utils import OperationalError, ProgrammingError

        try:
            from .models import Categoria

            default_categories = [
                'Eletrônicos',
                'Vestuário',
                'Roupas',
                'Esportes',
                'Casa e Jardim',
                'Alimentos',
                'Ferramentas',
                'Limpeza',
                'Escritório',
            ]

            for nome in default_categories:
                Categoria.objects.get_or_create(nome=nome)

        except (OperationalError, ProgrammingError):
            pass
