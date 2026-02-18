import pytest
from django.core.exceptions import ValidationError
from accounts.models import User


class TestUserModel:

    def test_criar_user_suces(self):
        user = User.objects.create_user(
            email="test@examplo.com",
            nome="helton",
            role=User.Cargo.ALUNO,
            password="senha123"
        )
        assert user.email == "test@exemplo.com"
        assert user.nome == "Heltom"
        assert user.role == User.Cargo.ALUNO
        assert user.check_password("senha123")

    def test_criar_sem_email(self):
        with pytest.raises(ValidationError):
            User.objects.create_user(
                email="",
                nome="helton",
                role=User.Cargo.ALUNO,
                password="senha123"
            )

    def test_criar_sem_nome(self):
        with pytest.raises(ValidationError):
            User.objects.create_user(
                email="test@exemplo.com",
                nome="",
                role=User.Cargo.ALUNO,
                password="senha123"
            )

    def test_criar_sem_role(self):
        with pytest.raises(ValidationError):
            User.objects.create_user(
                email="test@exemplo.com",
                nome="helton",
                role=None,
                password="senha123"
            )

    def test_criar_sem_senha(self):
        with pytest.raises(ValidationError):
            User.objects.create_user(
                email="test@exemplo.com",
                nome="helton",
                role=User.Cargo.ALUNO,
                password=""
            )

    def test_criar_senha_curta(self):
        with pytest.raises(ValidationError):
            User.objects.create_user(
                email="test@exemplo.com",
                nome="helton",
                role=User.Cargo.ALUNO,
                password="123"
            )

    def test_criar_superuser(self):
        superuser = User.objects.create_superuser(
            email="admin@exemplo.com",
            nome="admin",
            role=User.Cargo.ADMIN,
            password="senha123"
        )
        assert superuser.is_superuser is True
        assert superuser.is_staff is True
        assert superuser.is_active is True
        assert superuser.role == User.Cargo.ADMIN

    def test_criar_representacao_str(self):
        user = User.objects.create_user(
            email="test@exemplo.com",
            nome="helton",
            role=User.Cargo.ALUNO,
            password="senha123"
        )
        assert str(user) == "helton (test@exemplo.com)"
