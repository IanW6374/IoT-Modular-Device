"""Bounded role-based portal identity management for IoT-MD v2."""

try:
    import uos as os
except ImportError:
    import os

import credential_security
import credential_store
from portal_routes import ROLE_LEVELS, required_role, role_allows


def _find(config, username):
    folded = str(username).lower()
    return next((
        user for user in config.get('portal', {}).get('users', ())
        if str(user.get('username', '')).lower() == folded
    ), None)


def _policy(max_retries, session_timeout_s):
    if isinstance(max_retries, bool) or isinstance(session_timeout_s, bool):
        raise ValueError('portal user security values must be integers')
    try:
        max_retries = int(max_retries)
        session_timeout_s = int(session_timeout_s)
    except (TypeError, ValueError):
        raise ValueError('portal user security values must be integers')
    if not 1 <= max_retries <= 20:
        raise ValueError('maximum retries must be between 1 and 20')
    if not 300 <= session_timeout_s <= 86400:
        raise ValueError('session timeout must be between 5 and 1440 minutes')
    return max_retries, session_timeout_s


def _public(user):
    retries = int(user.get('max_retries', 5) or 5)
    failures = int(user.get('failed_attempts', 0) or 0)
    return {
        'username': user['username'], 'role': user['role'],
        'enabled': bool(user['enabled']), 'max_retries': retries,
        'failed_attempts': failures, 'locked': bool(user.get('locked')),
        'session_timeout_s': int(user.get('session_timeout_s', 3600) or 3600),
        'password_change_required': bool(user.get('password_change_required')),
    }


def list_users():
    config = credential_store.load(require_provisioned=True)
    return [_public(user) for user in config['portal']['users']]


async def authenticate(username, password):
    config = credential_store.load(require_provisioned=True)
    user = _find(config, username)
    if not user or not user.get('enabled') or user.get('locked'):
        return None
    verifier = user.get('password_verifier', '')
    matched = await credential_security.verify_password_async(password, verifier)
    # Re-read after the asynchronous password calculation. The following
    # synchronous update is then atomic with respect to the cooperative loop.
    config = credential_store.load(require_provisioned=True)
    user = _find(config, username)
    if (
        not user or not user.get('enabled') or user.get('locked') or
        user.get('password_verifier', '') != verifier
    ):
        return None
    if matched:
        if user.get('failed_attempts', 0):
            user['failed_attempts'] = 0
            credential_store.save(config)
        return _public(user)
    maximum = int(user.get('max_retries', 5) or 5)
    user['failed_attempts'] = min(
        maximum, int(user.get('failed_attempts', 0) or 0) + 1
    )
    user['locked'] = user['failed_attempts'] >= maximum
    credential_store.save(config)
    return None


def add_user(username, password, role='viewer', max_retries=5,
             session_timeout_s=3600, password_change_required=False):
    username = str(username).strip()
    role = str(role)
    credential_security.validate_password_strength(password)
    config = credential_store.load(require_provisioned=True)
    if _find(config, username):
        raise ValueError('portal username already exists')
    users = config['portal']['users']
    if len(users) >= credential_store.MAX_PORTAL_USERS:
        raise ValueError('portal user limit reached')
    if role not in credential_store.PORTAL_ROLES:
        raise ValueError('portal user role is invalid')
    max_retries, session_timeout_s = _policy(max_retries, session_timeout_s)
    verifier = credential_security.password_verifier(
        password, os.urandom(credential_security.PASSWORD_SALT_BYTES)
    )
    users.append({
        'username': username, 'password_verifier': verifier,
        'role': role, 'enabled': True,
        'max_retries': max_retries, 'failed_attempts': 0, 'locked': False,
        'session_timeout_s': session_timeout_s,
        'password_change_required': bool(password_change_required),
    })
    credential_store.save(config)
    return _public(users[-1])


def add_user_from_form(values):
    return add_user(
        values.get('username', ''), values.get('password', ''),
        values.get('role', 'viewer'), values.get('max_retries', 5),
        int(values.get('session_timeout_minutes', 60)) * 60,
        values.get('password_change_required') == 'true'
    )


def update_user(username, role=None, enabled=None, password=None,
                new_username=None, max_retries=None, session_timeout_s=None,
                reset_lockout=False, password_change_required=None):
    config = credential_store.load(require_provisioned=True)
    user = _find(config, username)
    if not user:
        raise ValueError('portal user does not exist')
    administrators = [
        item for item in config['portal']['users']
        if item.get('role') == 'administrator' and item.get('enabled')
    ]
    removes_last_administrator = (
        user.get('role') == 'administrator' and user.get('enabled') and
        ((role is not None and str(role) != 'administrator') or enabled is False)
    )
    if removes_last_administrator and len(administrators) <= 1:
        raise ValueError('at least one enabled portal administrator is required')
    if role is not None:
        role = str(role)
        if role not in credential_store.PORTAL_ROLES:
            raise ValueError('portal user role is invalid')
        user['role'] = role
    if enabled is not None:
        user['enabled'] = bool(enabled)
    if max_retries is not None or session_timeout_s is not None:
        retries, timeout = _policy(
            user.get('max_retries', 5) if max_retries is None else max_retries,
            user.get('session_timeout_s', 3600)
            if session_timeout_s is None else session_timeout_s
        )
        user['max_retries'], user['session_timeout_s'] = retries, timeout
        if int(user.get('failed_attempts', 0) or 0) >= retries:
            user['locked'] = True
    if new_username is not None:
        new_username = str(new_username).strip()
        if not new_username or len(new_username) > 32:
            raise ValueError('portal username must contain 1..32 characters')
        existing = _find(config, new_username)
        if existing is not None and existing is not user:
            raise ValueError('portal username already exists')
        old_username = str(user.get('username', ''))
        user['username'] = new_username
        if str(config['portal'].get('username', '')).lower() == old_username.lower():
            config['portal']['username'] = new_username
    if password is not None:
        credential_security.validate_password_strength(password)
        user['password_verifier'] = credential_security.password_verifier(
            password, os.urandom(credential_security.PASSWORD_SALT_BYTES)
        )
        reset_lockout = True
        user['password_change_required'] = False
    elif password_change_required is not None:
        user['password_change_required'] = bool(password_change_required)
    if reset_lockout:
        user['failed_attempts'], user['locked'] = 0, False
    credential_store.save(config)
    return _public(user)


def update_user_from_form(values):
    username = values.get('username', '')
    result = update_user(
        username, role=values.get('role', 'viewer'),
        enabled=values.get('enabled') == 'true',
        new_username=values.get('new_username', username),
        max_retries=values.get('max_retries'),
        session_timeout_s=(
            int(values['session_timeout_minutes']) * 60
            if values.get('session_timeout_minutes') else None
        ), reset_lockout=values.get('reset_lockout') == 'true',
        password_change_required=(
            values.get('password_change_required') == 'true'
        )
    )
    result['previous_username'] = username
    return result


def remove_user(username):
    config = credential_store.load(require_provisioned=True)
    users = config['portal']['users']
    target = _find(config, username)
    if not target:
        return False
    if (
        target.get('role') == 'administrator' and target.get('enabled') and
        len([
            item for item in users
            if item.get('role') == 'administrator' and item.get('enabled')
        ]) <= 1
    ):
        raise ValueError('at least one enabled portal administrator is required')
    users.remove(target)
    credential_store.save(config)
    return True
