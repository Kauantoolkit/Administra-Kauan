from django.contrib.messages.storage.base import BaseStorage, Message
from django.contrib.messages.constants import INFO

class EstoqueStorage(BaseStorage):
    """
    Storage personalizada só para mensagens de estoque.
    Não interfere nas mensagens normais do Django.
    """

    _estoque_messages = []

    def _get(self, *args, **kwargs):
        # Retorna mensagens apenas dessa storage
        return (self._estoque_messages, True)

    def _store(self, messages, response, *args, **kwargs):
        # Armazena mensagens de estoque
        self._estoque_messages = list(messages)
        return [] 