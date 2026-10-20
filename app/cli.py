import argparse
import getpass
import sys

from . import auth, config, db, security


def _connect():
    config.data_dir().mkdir(parents=True, exist_ok=True)
    conn = db.connect(config.db_path())
    db.migrate(conn)
    return conn


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    first = getpass.getpass("Password: ")
    second = getpass.getpass("Repeat password: ")
    if first != second:
        raise SystemExit("passwords do not match")
    return first


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-user", help="create the first user")
    create.add_argument("--name", required=True)
    create.add_argument("--password-stdin", action="store_true")
    reset = commands.add_parser("reset-password", help="set a new password and unlock the account")
    reset.add_argument("--name")
    reset.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args(argv)

    conn = _connect()
    try:
        password = _read_password(args.password_stdin)
        if args.command == "create-user":
            auth.create_user(conn, args.name, password)
            print(f"user {args.name} created")
        else:
            name = auth.reset_password(conn, args.name, password)
            print(f"password reset for {name}; all sessions were closed")
    except (security.WeakPassword, auth.UserExists, auth.UserNotFound) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
