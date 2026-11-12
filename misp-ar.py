#!/usr/bin/env python3
"""
misp-ar: Wazuh Active Response script for MISP IoCs (Windows).

Reads a Wazuh alert (JSON) from stdin and, depending on the MISP IoC type:
  - ip-src / ip-dst / ip : blocks inbound traffic with Windows Firewall (netsh)
  - domain               : sinkholes the domain in the hosts file (0.0.0.0)
  - sha256               : deletes the malicious file
Supports the Wazuh "add" and "delete" commands (delete = undo after timeout).
"""
import ipaddress
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LOG_FILE = r"C:\Program Files (x86)\ossec-agent\active-response\active-responses.log"
HOSTS_FILE = r"C:\Windows\System32\drivers\etc\hosts"
RULE_PREFIX = "MISP-AR Block"

DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$", re.I)
SHA256_RE = re.compile(r"^[A-Fa-f0-9]{64}$")


def write_log(message: str) -> None:
    """Append a timestamped message to the active-response log."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y/%m/%d %H:%M:%S} misp-ar: {message}\n")
    except OSError:
        pass  # never crash because logging failed


def delete_file(path: str) -> None:
    """Delete a file if it exists; log the outcome."""
    try:
        if os.path.isfile(path):
            os.remove(path)
            write_log(f"File removed: {path}")
        else:
            write_log(f"File not found, nothing to remove: {path}")
    except Exception as exc:
        write_log(f"ERROR deleting file {path}: {exc}")


def block_ip(ip: str) -> None:
    """Create an inbound-block firewall rule for the given IP."""
    try:
        ipaddress.ip_address(ip)
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "add", "rule",
             f"name={RULE_PREFIX} {ip}", "dir=in", "action=block", f"remoteip={ip}"],
            check=True, capture_output=True, text=True,
        )
        write_log(f"IP blocked: {ip}")
    except Exception as exc:
        write_log(f"ERROR blocking IP {ip}: {exc}")


def unblock_ip(ip: str) -> None:
    try:
        ipaddress.ip_address(ip)
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={RULE_PREFIX} {ip}"],
            check=True, capture_output=True, text=True,
        )
        write_log(f"IP unblocked: {ip}")
    except Exception as exc:
        write_log(f"ERROR unblocking IP {ip}: {exc}")


def block_domain(domain: str) -> None:
    """Redirect the domain to 0.0.0.0 in the hosts file."""
    try:
        if not DOMAIN_RE.match(domain):
            raise ValueError("invalid domain")
        entry = f"0.0.0.0 {domain}"
        with open(HOSTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
            if any(line.strip().lower() == entry.lower() for line in f):
                write_log(f"Domain already blocked: {domain}")
                return
        with open(HOSTS_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{entry}\n")
        write_log(f"Domain blocked: {domain}")
    except Exception as exc:
        write_log(f"ERROR blocking domain {domain}: {exc}")


def unblock_domain(domain: str) -> None:
    try:
        entry = f"0.0.0.0 {domain}".lower()
        with open(HOSTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        with open(HOSTS_FILE, "w", encoding="utf-8") as f:
            f.writelines(l for l in lines if l.strip().lower() != entry)
        write_log(f"Domain unblocked: {domain}")
    except Exception as exc:
        write_log(f"ERROR unblocking domain {domain}: {exc}")


def main() -> None:
    try:
        data = json.loads(sys.stdin.readline())
    except Exception as exc:
        write_log(f"ERROR reading JSON from stdin: {exc}")
        sys.exit(1)

    command = data.get("command", "add")
    alert = data.get("parameters", {}).get("alert", {})
    misp = alert.get("data", {}).get("misp", {})
    ioc_type = str(misp.get("type", "")).lower()
    ioc_value = str(misp.get("value", "")).strip()

    if not ioc_type or not ioc_value:
        write_log("No MISP IoC found in alert; nothing to do.")
        sys.exit(0)

    write_log(f"Received command={command} type={ioc_type} value={ioc_value}")

    if ioc_type in ("ip-src", "ip-dst", "ip"):
        (block_ip if command == "add" else unblock_ip)(ioc_value)
    elif ioc_type == "domain":
        (block_domain if command == "add" else unblock_domain)(ioc_value)
    elif ioc_type == "sha256":
        if command == "add":
            if not SHA256_RE.match(ioc_value):
                write_log(f"Invalid SHA256: {ioc_value}")
            else:
                path = alert.get("syscheck", {}).get("path") or misp.get("path", "")
                if path:
                    delete_file(path)
                else:
                    write_log(f"SHA256 {ioc_value} matched but no file path in alert.")
    else:
        write_log(f"Unsupported IoC type: {ioc_type}")


if __name__ == "__main__":
    main()
