"""Run SSH command on remote server."""
import os
import sys

try:
    import paramiko
except ImportError as exc:
    raise SystemExit("Paramiko is required. Install it with: pip install paramiko") from exc


def run(cmd: str) -> str:
    host = os.getenv("PORTFOLIO_SSH_HOST")
    user = os.getenv("PORTFOLIO_SSH_USER", "root")
    port = int(os.getenv("PORTFOLIO_SSH_PORT", "22"))
    password = os.getenv("PORTFOLIO_SSH_PASSWORD")
    key_path = os.getenv("PORTFOLIO_SSH_KEY_PATH")

    if not host:
        raise RuntimeError("Set PORTFOLIO_SSH_HOST before running ssh_cmd.py")
    if not password and not key_path:
        raise RuntimeError("Set PORTFOLIO_SSH_PASSWORD or PORTFOLIO_SSH_KEY_PATH before running ssh_cmd.py")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {
        "hostname": host,
        "port": port,
        "username": user,
        "timeout": 15,
    }
    if key_path:
        connect_kwargs["key_filename"] = os.path.expanduser(key_path)
        connect_kwargs["look_for_keys"] = False
    if password:
        connect_kwargs["password"] = password
        connect_kwargs["look_for_keys"] = False
        connect_kwargs["allow_agent"] = False

    client.connect(**connect_kwargs)
    stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    client.close()
    return out + err


if __name__ == "__main__":
    cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "uname -a"
    sys.stdout.buffer.write((run(cmd) + "\n").encode("utf-8", errors="replace"))
