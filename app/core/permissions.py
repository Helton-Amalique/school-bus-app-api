"""
core/permissions.py
Permissões granulares do sistema de transporte escolar.
"""

from rest_framework.permissions import BasePermission, IsAuthenticated


def _tem_role(user, *roles) -> bool:
    """Devolve True se o utilizador autenticado tiver um dos roles indicados."""
    return bool(user and user.is_authenticated and user.role in roles)


def _e_admin_ou_gestor(user) -> bool:
    return user.is_staff or _tem_role(user, 'ADMIN', 'GESTOR')


class IsGestor(BasePermission):
    """
    Permite acesso a utilizadores com role GESTOR ou ADMIN (is_staff).
    Usado para operações de gestão: criar, editar, apagar.
    """
    message = 'Acesso restrito a gestores.'

    def has_permission(self, request, view):
        return _e_admin_ou_gestor(request.user)


class IsMotorista(BasePermission):
    """
    Permite acesso a utilizadores com role MOTORISTA.
    Usado para operações de frota: abastecimentos, estado do veículo.
    """
    message = 'Acesso restrito a motoristas.'

    def has_permission(self, request, view):
        return _tem_role(request.user, 'MOTORISTA')


class IsMonitor(BasePermission):
    """
    Permite acesso a utilizadores com role MONITOR.
    Usado para registo de embarque/desembarque.
    """
    message = 'Acesso restrito a monitores.'

    def has_permission(self, request, view):
        return _tem_role(request.user, 'MONITOR')


class IsEncarregado(BasePermission):
    """
    Permite acesso a utilizadores com role ENCARREGADO.
    Usado para consulta dos seus alunos e mensalidades.
    """
    message = 'Acesso restrito a encarregados de educação.'

    def has_permission(self, request, view):
        return _tem_role(request.user, 'ENCARREGADO')


class IsAluno(BasePermission):
    """
    Permite acesso a utilizadores com role ALUNO.
    Usado para consulta do próprio perfil e rota.
    """
    message = 'Acesso restrito a alunos.'

    def has_permission(self, request, view):
        return _tem_role(request.user, 'ALUNO')


class IsGestorOuMotorista(BasePermission):
    """GESTOR ou MOTORISTA — gestão + operação de frota."""
    message = 'Acesso restrito a gestores ou motoristas.'

    def has_permission(self, request, view):
        return _e_admin_ou_gestor(request.user) or _tem_role(request.user, 'MOTORISTA')


class IsGestorOuMonitor(BasePermission):
    """GESTOR ou MONITOR — gestão + acompanhamento de rotas."""
    message = 'Acesso restrito a gestores ou monitores.'

    def has_permission(self, request, view):
        return _e_admin_ou_gestor(request.user) or _tem_role(request.user, 'MONITOR')


class IsGestorOuMotoristaOuMonitor(BasePermission):
    """GESTOR, MOTORISTA ou MONITOR — operação de transporte."""
    message = 'Acesso restrito a gestores, motoristas ou monitores.'

    def has_permission(self, request, view):
        return (
            _e_admin_ou_gestor(request.user)
            or _tem_role(request.user, 'MOTORISTA', 'MONITOR')
        )


class IsGestorOuEncarregado(BasePermission):
    """GESTOR ou ENCARREGADO — gestão + consulta parental."""
    message = 'Acesso restrito a gestores ou encarregados.'

    def has_permission(self, request, view):
        return _e_admin_ou_gestor(request.user) or _tem_role(request.user, 'ENCARREGADO')


class IsGestorOuProprioAluno(BasePermission):
    """
    GESTOR pode ver qualquer aluno.
    ALUNO só pode ver o seu próprio perfil (verificado no has_object_permission).
    """
    message = 'Acesso restrito a gestores ou ao próprio aluno.'

    def has_permission(self, request, view):
        return (
            _e_admin_ou_gestor(request.user)
            or _tem_role(request.user, 'ALUNO', 'ENCARREGADO', 'MONITOR', 'MOTORISTA')
        )

    def has_object_permission(self, request, view, obj):
        if _e_admin_ou_gestor(request.user):
            return True
        # Aluno só vê o próprio
        if _tem_role(request.user, 'ALUNO'):
            return obj.user == request.user
        # Encarregado só vê os seus alunos
        if _tem_role(request.user, 'ENCARREGADO'):
            try:
                return obj.encarregado.user == request.user
            except AttributeError:
                return False
        # Monitor e Motorista vêem todos os alunos (leitura)
        return _tem_role(request.user, 'MONITOR', 'MOTORISTA')


class IsProprioPerfilOuGestor(BasePermission):
    """
    Qualquer utilizador pode ver/editar o seu próprio perfil.
    Apenas GESTOR/ADMIN pode ver/editar perfis alheios.
    """
    message = 'Só pode aceder ao seu próprio perfil.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if _e_admin_ou_gestor(request.user):
            return True
        user_do_obj = obj if hasattr(obj, 'email') else getattr(obj, 'user', None)
        return user_do_obj == request.user


class PodeLerMensalidade(BasePermission):
    """
    GESTOR → todas as mensalidades.
    ENCARREGADO → só mensalidades dos seus alunos.
    ALUNO → só a sua própria mensalidade.
    MOTORISTA / MONITOR → sem acesso.
    """
    message = 'Sem permissão para ver esta mensalidade.'

    def has_permission(self, request, view):
        return (
            _e_admin_ou_gestor(request.user)
            or _tem_role(request.user, 'ENCARREGADO', 'ALUNO')
        )

    def has_object_permission(self, request, view, obj):
        if _e_admin_ou_gestor(request.user):
            return True
        if _tem_role(request.user, 'ALUNO'):
            return obj.aluno.user == request.user
        if _tem_role(request.user, 'ENCARREGADO'):
            try:
                return obj.aluno.encarregado.user == request.user
            except AttributeError:
                return False
        return False


class PodeVerRota(BasePermission):
    """
    GESTOR / MOTORISTA / MONITOR → todas as rotas.
    ENCARREGADO → rotas onde tem alunos inscritos.
    ALUNO → rota em que está inscrito.
    """
    message = 'Sem permissão para ver esta rota.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if _e_admin_ou_gestor(request.user):
            return True
        if _tem_role(request.user, 'MOTORISTA'):
            return obj.veiculo.motorista.user == request.user
        if _tem_role(request.user, 'MONITOR'):
            return True
        if _tem_role(request.user, 'ALUNO'):
            return obj.alunos.filter(user=request.user).exists()
        if _tem_role(request.user, 'ENCARREGADO'):
            try:
                alunos_enc = request.user.perfil_encarregado.alunos.values_list('pk', flat=True)
                return obj.alunos.filter(pk__in=alunos_enc).exists()
            except AttributeError:
                return False
        return False


class PodeVerVeiculo(BasePermission):
    """
    GESTOR / MONITOR → todos os veículos.
    MOTORISTA → só os seus veículos.
    ENCARREGADO / ALUNO → sem acesso directo a veículos.
    """
    message = 'Sem permissão para ver este veículo.'

    def has_permission(self, request, view):
        return (
            _e_admin_ou_gestor(request.user)
            or _tem_role(request.user, 'MOTORISTA', 'MONITOR')
        )

    def has_object_permission(self, request, view, obj):
        if _e_admin_ou_gestor(request.user) or _tem_role(request.user, 'MONITOR'):
            return True
        if _tem_role(request.user, 'MOTORISTA'):
            return obj.motorista.user == request.user
        return False
