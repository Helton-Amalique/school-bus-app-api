from rest_framework.permissions import BasePermission, SAFE_METHODS


def _tem_role(user, *roles):
    return user.is_authenticated and user.role in roles

def _is_admin(user):
    return user.is_authenticated and (user.is_staff or user.role == 'ADMIN')


class IsAdmin(BasePermission):
    """Apenas administradores (is_staff ou role=ADMIN)."""
    message = "Acesso reservado a administradores."

    def has_permission(self, request, view):
        return _is_admin(request.user)


class IsGestor(BasePermission):
    """Apenas gestores."""
    message = "Acesso reservado a gestores."

    def has_permission(self, request, view):
        return _tem_role(request.user, 'GESTOR')


class IsMotorista(BasePermission):
    """Apenas motoristas."""
    message = "Acesso reservado a motoristas."

    def has_permission(self, request, view):
        return _tem_role(request.user, 'MOTORISTA')


class IsMonitor(BasePermission):
    """Apenas monitores."""
    message = "Acesso reservado a monitores."

    def has_permission(self, request, view):
        return _tem_role(request.user, 'MONITOR')


class IsEncarregado(BasePermission):
    """Apenas encarregados."""
    message = "Acesso reservado a encarregados."

    def has_permission(self, request, view):
        return _tem_role(request.user, 'ENCARREGADO')


class IsAluno(BasePermission):
    """Apenas alunos."""
    message = "Acesso reservado a alunos."

    def has_permission(self, request, view):
        return _tem_role(request.user, 'ALUNO')


class IsAdminOrGestor(BasePermission):
    """Admin ou Gestor."""
    message = "Acesso reservado a administradores ou gestores."

    def has_permission(self, request, view):
        return _is_admin(request.user) or _tem_role(request.user, 'GESTOR')


class IsAdminOrMotorista(BasePermission):
    """Admin ou Motorista — ex: leitura de veículos."""
    message = "Acesso reservado a administradores ou motoristas."

    def has_permission(self, request, view):
        return _is_admin(request.user) or _tem_role(request.user, 'MOTORISTA')


class IsAdminOrMonitor(BasePermission):
    """Admin ou Monitor — ex: check-in/check-out."""
    message = "Acesso reservado a administradores ou monitores."

    def has_permission(self, request, view):
        return _is_admin(request.user) or _tem_role(request.user, 'MONITOR')


class IsMotoristaOrMonitor(BasePermission):
    """Motorista ou Monitor — operações em rota."""
    message = "Acesso reservado a motoristas ou monitores."

    def has_permission(self, request, view):
        return _tem_role(request.user, 'MOTORISTA', 'MONITOR')


class IsStaffOrReadOnly(BasePermission):
    """Leitura livre para autenticados, escrita apenas para staff."""
    message = "Apenas staff pode escrever."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return _is_admin(request.user)


class IsSelfOrAdmin(BasePermission):
    """O próprio utilizador ou admin pode aceder/editar o objeto."""
    message = "Não tem permissão para aceder a este recurso."

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if _is_admin(request.user):
            return True
        # Suporta objetos que sejam User diretamente
        if hasattr(obj, 'email'):
            return obj == request.user
        # Suporta perfis (Aluno, Motorista, etc.) com FK para user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class IsEncarregadoDoAluno(BasePermission):
    """Encarregado só acede aos seus próprios alunos."""
    message = "Não tem permissão para aceder a este aluno."

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if _is_admin(request.user) or _tem_role(request.user, 'GESTOR'):
            return True
        encarregado = getattr(request.user, 'encarregado', None)
        if not encarregado:
            return False
        # obj pode ser um Aluno ou um TransporteAluno
        aluno = obj if hasattr(obj, 'encarregado') else getattr(obj, 'aluno', None)
        return aluno and aluno.encarregado == encarregado


class IsGestorDaFrota(BasePermission):
    """Apenas gestores do departamento FROTA ou GERAL podem aprovar manutenções."""
    message = "Apenas gestores de frota podem executar esta ação."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if _is_admin(request.user):
            return True
        gestor = getattr(request.user, 'gestor', None)
        return gestor and gestor.pode_aprovar_manutencao()


class IsMotoristaDestaRota(BasePermission):
    """Motorista só pode operar na sua própria rota."""
    message = "Só pode operar na sua própria rota."

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if _is_admin(request.user):
            return True
        motorista = getattr(request.user, 'motorista', None)
        if not motorista:
            return False
        # obj pode ser Rota ou TransporteAluno
        rota = obj if hasattr(obj, 'veiculo') else getattr(obj, 'rota', None)
        return rota and rota.veiculo.motorista == motorista


class IsMonitorDestaRota(BasePermission):
    """Monitor só pode fazer check-in na sua rota ativa."""
    message = "Só pode operar na sua rota atribuída."

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if _is_admin(request.user):
            return True
        monitor = getattr(request.user, 'monitor', None)
        if not monitor:
            return False
        rota = obj if hasattr(obj, 'veiculo') else getattr(obj, 'rota', None)
        return rota and hasattr(rota, 'monitor') and rota.monitor == monitor


class ReadOnlyOrAdmin(BasePermission):
    """GET/HEAD/OPTIONS livres para autenticados. POST/PUT/DELETE apenas admin."""
    message = "Não tem permissão para modificar este recurso."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return _is_admin(request.user)
