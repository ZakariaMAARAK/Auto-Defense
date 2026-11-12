#!/usr/bin/python3
import os
import sys
import json
import hashlib
import subprocess
import datetime

LOG_FILE = r"C:\\Program Files (x86)\\ossec-agent\\active-response\\active-responses.log"
HOSTS_FILE = r"C:\\Windows\\System32\\drivers\\etc\\hosts"

def write_log(message):
    """Write a message to the active-response log."""
    try:
        with open(LOG_FILE, "a") as log_file:
            log_file.write(f"{datetime.datetime.now()} - {message}\n")
    except Exception as e:
        print(f"Error writing to log: {e}", file=sys.stderr)

def delete_file(file_path):
    """Delete the specified file permanently."""
    try:
        os.remove(file_path)
        write_log(f"File successfully deleted: {file_path}")
    except FileNotFoundError:
        write_log(f"File not found: {file_path}")
    except Exception as e:
        write_log(f"Error deleting file: {file_path}. Exception: {str(e)}")

def block_ip(ip_address):
    """Block the specified IP address using Windows Firewall."""
    try:
        rule_name = f"Block_IP_{ip_address}"
        result = subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "add", "rule",
                "name=" + rule_name,
                "dir=in",
                "action=block",
                "remoteip=" + ip_address
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            write_log(f"Successfully blocked IP address: {ip_address}")
        else:
            write_log(
                f"Failed to block IP address: {ip_address}\n"
                f"Return Code: {result.returncode}\n"
                f"Output: {result.stdout}\n"
                f"Error: {result.stderr}"
            )
    except Exception as e:
        write_log(f"Exception while blocking IP: {ip_address}. Exception: {str(e)}")

def block_domain(domain):
    """Block the specified domain by modifying the hosts file."""
    try:
        with open(HOSTS_FILE, "a") as hosts:
            hosts.write(f"0.0.0.0 {domain}\n")
        write_log(f"Successfully blocked domain: {domain}")
    except Exception as e:
        write_log(f"Error blocking domain: {domain}. Exception: {str(e)}")

def main():
    """Main function to process active response."""
    write_log("Active response started")

    try:
        # Read and parse the input from stdin
        input_data = sys.stdin.read()
        write_log(f"Raw input received: {input_data}")

        # Parse the JSON input
        alert = json.loads(input_data).get("parameters", {}).get("alert", {})
        data = alert.get("data", {}).get("misp", {})
        misp_type = data.get("type", "")
        misp_value = data.get("value", "")

        # Log parsed data for debugging
        write_log(f"Parsed MISP data - Type: {misp_type}, Value: {misp_value}")

        # Perform actions based on MISP type
        if misp_type == "sha256":
            for root, _, files in os.walk(r"C:\Users\LabUser\Desktop"):
                for file in files:
                    file_path = os.path.join(root, file)
                    write_log(f"Checking file: {file_path}")
                    with open(file_path, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                        if file_hash == misp_value:
                            delete_file(file_path)
                            sys.exit(0) # Exit after deleting the file
            write_log(f"No file found with hash: {misp_value}")
        elif misp_type == "ip-src" or misp_type == "ip-dst":
            block_ip(misp_value)
            sys.exit(0) # Exit after blocking the IP
        elif misp_type == "domain":
            block_domain(misp_value)
            sys.exit(0) # Exit after blocking the domain
        else:
            write_log(f"Unsupported MISP type: {misp_type}")

    except json.JSONDecodeError:
        write_log("Error decoding JSON input.")
    except Exception as e:
        write_log(f"Unexpected error: {str(e)}")
    finally:
        write_log("Active response completed.")
        sys.exit(0) # Ensure the script exits cleanly

if __name__ == "__main__":
    main()
