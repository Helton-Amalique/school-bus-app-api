from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from accounts.models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "email", "nome", "role", "is_staff", "is_active", "is_superuser")
    list_filter = ("is_staff", "is_active", "role", "is_superuser")
    search_fields = ("email", "nome")
    ordering = ("email",)
    readonly_fields = ("data_criacao", "data_atualizacao")

    fieldsets = (
        (None, {"fields": ("email", "nome", "password")}),
        ("Cargo", {"fields": ("role",)}),
        ("Permissões", {"fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
        ("Datas", {"fields": ("last_login", "data_criacao", "data_atualizacao")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "nome", "role", "password1", "password2"),
        }),
    )

    search_help_text = "Pesquisar por email ou nome"

    actions = ["marcar_como_ativo", "marcar_como_inativo"]

    def marcar_como_ativo(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} usuário(s) foram marcados como ativos.")
    marcar_como_ativo.short_description = "Marcar usuários selecionados como ativos"

    def marcar_como_inativo(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} usuário(s) foram marcados como inativos.")
    marcar_como_inativo.short_description = "Marcar usuários selecionados como inativos"
