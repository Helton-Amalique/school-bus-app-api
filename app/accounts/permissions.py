from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Permite acesso apenas a usuários com role ADMIN."""
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role == "ADMIN")

    def has_object_permission(self, request, view, obj):
        return bool(request.user.is_authenticated and request.user.role == "ADMIN")


class IsAluno(BasePermission):
    """Permite acesso apenas ao próprio perfil do aluno."""
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role == "ALUNO")

    def has_object_permission(self, request, view, obj):
        return hasattr(obj, "user") and obj.user == request.user


class IsEncarregado(BasePermission):
    """Permite acesso apenas ao encarregado e seus dependentes."""
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role == "ENCARREGADO")

    def has_object_permission(self, request, view, obj):
        # Se o objeto tiver relação direta com user
        if hasattr(obj, "user"):
            return obj.user == request.user
        # Se o objeto tiver relação com encarregado
        if hasattr(obj, "encarregado"):
            return obj.encarregado.user == request.user
        return False


class IsMotorista(BasePermission):
    """Permite acesso ao próprio perfil do motorista e aos alunos que transporta."""
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role == "MOTORISTA")

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "rota"):
            return obj.rota.veiculo.motorista.user == request.user
        return False
