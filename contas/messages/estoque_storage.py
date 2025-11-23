from django.contrib.messages.storage.base import BaseStorage, Message
from django.contrib.messages.constants import INFO

class EstoqueStorage(BaseStorage):
    _estoque_messages = []

    def _get(self, *args, **kwargs):
        return (self._estoque_messages, True)

    def _store(self, messages, response, *args, **kwargs):
        self._estoque_messages = list(messages)
        return [] 