"""Interactive local provisioning. No default public password."""
from getpass import getpass

from .auth import AuthStore
from .config import database_path
from .data_loader import load_dataset
from .config import BACKEND_DIR


def main():
    store = AuthStore(database_path())
    existing = store.db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    if existing and input('Accounts already exist. Replace their passwords and revoke sessions? [y/N] ').lower() != 'y':
        store.close()
        return
    valid = {e['employee_id'] for e in load_dataset(BACKEND_DIR / 'data').employees}
    employee = input('Employee account profile [E0002]: ').strip() or 'E0002'
    if employee not in valid:
        raise SystemExit('Unknown employee ID')
    passwords = {}
    for name in ('hr', 'employee'):
        password = getpass(f'New {name} password (at least 12 characters): ')
        if len(password) < 12 or password != getpass('Confirm password: '):
            raise SystemExit('Passwords must match and contain at least 12 characters. Nothing changed.')
        passwords[name] = password
    for name, password in passwords.items():
        store.add_user(name, password, name, employee if name == 'employee' else None)
    store.close()
    print('Created local hr and employee accounts. Run npm run dev from the repository root.')


if __name__ == '__main__':
    main()
