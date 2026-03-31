from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from touch_panel_studio.core.security import PasswordService
from touch_panel_studio.db.models.user import User
from touch_panel_studio.domain.enums.roles import UserRole


@dataclass(frozen=True, slots=True)
class AuthResult:
    ok: bool
    message: str
    user_id: int | None = None
    role: UserRole | None = None


@dataclass(frozen=True, slots=True)
class AuthService:
    passwords: PasswordService

    MIN_PASSWORD_LEN = 5

    def _get_user(self, session: Session, user_id: int) -> User | None:
        return session.get(User, int(user_id))

    def _is_admin(self, session: Session, user_id: int) -> bool:
        u = self._get_user(session, user_id)
        return bool(u and u.is_active and u.role == UserRole.admin)

    def _normalize_username(self, username: str) -> str:
        return username.strip().lower()

    def _username_exists(self, session: Session, username: str, *, exclude_user_id: int | None = None) -> bool:
        u = self._normalize_username(username)
        q = select(User.id).where(func.lower(User.username) == u)
        if exclude_user_id is not None:
            q = q.where(User.id != int(exclude_user_id))
        return session.scalar(q.limit(1)) is not None

    def authenticate(self, session: Session, username: str, password: str) -> AuthResult:
        username = self._normalize_username(username)
        if not username or not password:
            return AuthResult(ok=False, message="Введите логин и пароль.")

        user = session.scalar(select(User).where(func.lower(User.username) == username))
        if not user or not user.is_active:
            return AuthResult(ok=False, message="Неверный логин или пароль.")

        if not self.passwords.verify_password(user.password_hash, password):
            return AuthResult(ok=False, message="Неверный логин или пароль.")

        return AuthResult(ok=True, message="OK", user_id=user.id, role=user.role)

    def has_any_user(self, session: Session) -> bool:
        return session.scalar(select(User.id).limit(1)) is not None

    def create_first_admin(self, session: Session, username: str, password: str) -> AuthResult:
        username = self._normalize_username(username)
        if len(username) < 3:
            return AuthResult(ok=False, message="Логин слишком короткий.")
        if len(password) < self.MIN_PASSWORD_LEN:
            return AuthResult(ok=False, message=f"Пароль должен быть не короче {self.MIN_PASSWORD_LEN} символов.")
        if self.has_any_user(session):
            return AuthResult(ok=False, message="Администратор уже создан.")

        password_hash = self.passwords.hash_password(password)
        user = User(username=username, password_hash=password_hash, role=UserRole.admin, is_active=True)
        session.add(user)
        session.commit()
        session.refresh(user)
        return AuthResult(ok=True, message="Администратор создан.", user_id=user.id, role=user.role)

    # --- Profile (self-service) ---
    def change_own_username(self, session: Session, user_id: int, *, current_password: str, new_username: str) -> AuthResult:
        u = self._get_user(session, user_id)
        if not u or not u.is_active:
            return AuthResult(ok=False, message="Пользователь не найден.")
        if not self.passwords.verify_password(u.password_hash, current_password or ""):
            return AuthResult(ok=False, message="Неверный текущий пароль.")
        new_u = self._normalize_username(new_username)
        if len(new_u) < 3:
            return AuthResult(ok=False, message="Логин слишком короткий.")
        if self._username_exists(session, new_u, exclude_user_id=u.id):
            return AuthResult(ok=False, message="Такой логин уже занят.")
        u.username = new_u
        session.add(u)
        session.commit()
        return AuthResult(ok=True, message="Логин обновлён.", user_id=u.id, role=u.role)

    def change_own_password(self, session: Session, user_id: int, *, current_password: str, new_password: str) -> AuthResult:
        u = self._get_user(session, user_id)
        if not u or not u.is_active:
            return AuthResult(ok=False, message="Пользователь не найден.")
        if not self.passwords.verify_password(u.password_hash, current_password or ""):
            return AuthResult(ok=False, message="Неверный текущий пароль.")
        if len(new_password or "") < self.MIN_PASSWORD_LEN:
            return AuthResult(ok=False, message=f"Новый пароль должен быть не короче {self.MIN_PASSWORD_LEN} символов.")
        u.password_hash = self.passwords.hash_password(new_password)
        session.add(u)
        session.commit()
        return AuthResult(ok=True, message="Пароль обновлён.", user_id=u.id, role=u.role)

    # --- Admin user management ---
    def list_users(self, session: Session, actor_user_id: int) -> tuple[AuthResult, list[User]]:
        if not self._is_admin(session, actor_user_id):
            return AuthResult(ok=False, message="Нет прав администратора."), []
        users = list(session.scalars(select(User).order_by(User.id.asc())))
        return AuthResult(ok=True, message="OK"), users

    def admin_create_user(
        self,
        session: Session,
        actor_user_id: int,
        *,
        username: str,
        password: str,
        role: UserRole,
        is_active: bool = True,
    ) -> AuthResult:
        if not self._is_admin(session, actor_user_id):
            return AuthResult(ok=False, message="Нет прав администратора.")
        u = self._normalize_username(username)
        if len(u) < 3:
            return AuthResult(ok=False, message="Логин слишком короткий.")
        if len(password or "") < self.MIN_PASSWORD_LEN:
            return AuthResult(ok=False, message=f"Пароль должен быть не короче {self.MIN_PASSWORD_LEN} символов.")
        if self._username_exists(session, u):
            return AuthResult(ok=False, message="Такой логин уже занят.")
        try:
            r = role if isinstance(role, UserRole) else UserRole(str(role))
        except Exception:
            r = UserRole.viewer
        user = User(username=u, password_hash=self.passwords.hash_password(password), role=r, is_active=bool(is_active))
        session.add(user)
        session.commit()
        session.refresh(user)
        return AuthResult(ok=True, message="Пользователь создан.", user_id=user.id, role=user.role)

    def admin_update_user(
        self,
        session: Session,
        actor_user_id: int,
        target_user_id: int,
        *,
        username: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
        new_password: str | None = None,
    ) -> AuthResult:
        if not self._is_admin(session, actor_user_id):
            return AuthResult(ok=False, message="Нет прав администратора.")
        u = self._get_user(session, target_user_id)
        if not u:
            return AuthResult(ok=False, message="Пользователь не найден.")

        if username is not None:
            nu = self._normalize_username(username)
            if len(nu) < 3:
                return AuthResult(ok=False, message="Логин слишком короткий.")
            if self._username_exists(session, nu, exclude_user_id=u.id):
                return AuthResult(ok=False, message="Такой логин уже занят.")
            u.username = nu

        if role is not None:
            try:
                u.role = role if isinstance(role, UserRole) else UserRole(str(role))
            except Exception:
                return AuthResult(ok=False, message="Некорректная роль.")

        if is_active is not None:
            # Не даём админу случайно отключить сам себя (иначе можно «запереться»).
            if int(actor_user_id) == int(u.id) and not bool(is_active):
                return AuthResult(ok=False, message="Нельзя отключить самого себя.")
            u.is_active = bool(is_active)

        if new_password is not None and str(new_password) != "":
            if len(new_password) < self.MIN_PASSWORD_LEN:
                return AuthResult(ok=False, message=f"Новый пароль должен быть не короче {self.MIN_PASSWORD_LEN} символов.")
            u.password_hash = self.passwords.hash_password(new_password)

        session.add(u)
        session.commit()
        return AuthResult(ok=True, message="Пользователь обновлён.", user_id=u.id, role=u.role)

