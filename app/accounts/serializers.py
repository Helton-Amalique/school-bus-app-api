"""Serializers for the accounts ."""

from rest_framework import serializers
from django.contrib.auth import (get_user_model, authenticate)
from django.utils.translation import gettext_lazy as _
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer para o modelo User."""
    class Meta:
        model = get_user_model()
        fields = ['email', "password", 'nome', 'role']
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8}
        }

    def create(self, validated_data):
        """Cria e retorna um usuário com senha criptografada."""
        password = validated_data.pop('password', None)
        return get_user_model().objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        """"""
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()
        return user


class AuthTokenSerializer(serializers.Serializer):
    """serializer para autenticacao do usuarios via token"""
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False,
    )

    def validate(self, attrs):
        """validacao e authenticacao do user"""
        email = attrs.get('email')
        password = attrs.get('password')
        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password
        )
        if not user:
            msg = _('Nao foi possivel autenticar com as credencias fornecidas')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs
