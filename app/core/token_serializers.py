"""
core/token_serializers.py
=========================
Serializer JWT customizado.

Adiciona `nome`, `role` e `nome_curto` ao payload do access token,
evitando um segundo request para obter o perfil após o login.

Referenciado em settings.py:
  SIMPLE_JWT = {
      'TOKEN_OBTAIN_SERIALIZER': 'core.token_serializers.CustomTokenObtainPairSerializer',
  }
"""

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Estende o token JWT com claims do utilizador:
      - nome       → nome completo
      - nome_curto → primeiro nome (para UI)
      - role       → cargo/papel no sistema
      - is_staff   → flag de administrador
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['nome'] = user.nome
        token['nome_curto'] = user.nome_curto
        token['role'] = user.role
        token['is_staff'] = user.is_staff

        return token
