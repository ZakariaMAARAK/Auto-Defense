# 🛡️ MISP + Wazuh Active Response: Automated Threat Mitigation

> Automating cyber defense: Wazuh consumes **MISP** threat intelligence and a custom Python Active Response script blocks malicious IPs, sinkholes malicious domains and purges malicious files on Windows endpoints, with no manual intervention.

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![Wazuh](https://img.shields.io/badge/Wazuh-SIEM%2FXDR-0A66C2)
![MISP](https://img.shields.io/badge/MISP-Threat%20Intel-orange)
![Platform](https://img.shields.io/badge/Endpoint-Windows-lightgrey?logo=windows)
![License](https://img.shields.io/badge/License-MIT-green)

---

##  Overview:

Manual response to threat intelligence is slow. This project closes the gap between **detection** and **response** by integrating:

- **MISP** (Malware Information Sharing Platform): source of Indicators of Compromise (IoCs)
- **Wazuh** (SIEM/XDR): correlates events with MISP IoCs and triggers Active Response
- **A custom Python script** (`auto_misp.py`), then it will be compiled to `.exe` via PyInstaller, that executes the mitigation on the endpoint

  

| IoC type (MISP) | Automated action | Mechanism |
|---|---|---|
| `ip-src` / IP address | Block inbound traffic | Windows Firewall rule via `netsh` |
| `domain` | Sinkhole the domain | Redirect to `0.0.0.0` in the `hosts` file |
| `sha256` | Delete the malicious file | `os.remove()` on the detected path |

Every action and error is written to an audit log (`active-responses.log`).

## Workflow conception:

<img width="3960" height="1078" alt="image" src="https://github.com/user-attachments/assets/d1dceeab-b1c0-4c0e-a9ed-40e7bc3ebfc4" />

The diagram covers both the **build/deploy pipeline** (Python script → PyInstaller → `.exe` → agent) and the **runtime detection/response flow**.

<p align="center">
  <a href="docs/architecture.png">
    <img src="docs/architecture.svg" alt="Architecture: MISP, Wazuh and Active Response workflow with PyInstaller build" width="100%">
  </a>
</p>

<p align="center"><sub>🔍 Click the diagram to open it at full resolution.</sub></p>



##  Project Files:

| File | Description |
|---|---|
| [`src/auto_misp.py`](src/auto_misp.py) | Active Response script (source code) |
| [`config/local_rules.xml`](config/local_rules.xml) | Custom Wazuh rules `200003` (domain) and `200004` (SHA256) |
| [`config/ossec.conf.snippet`](config/ossec.conf.snippet) | Wazuh manager `<command>` and `<active-response>` configuration |

##  Setup:

### 1. Endpoint (Windows agent): build with PyInstaller

[PyInstaller](https://pyinstaller.org) bundles the Python script and its interpreter into a single `.exe`, so the endpoint **does not need Python installed**.


```powershell
pip install -r requirements-build.txt

# --onefile: single standalone .exe   |   -w: no console window
pyinstaller.exe --onefile -w --name auto_misp src\auto_misp.py

Copy-Item .\dist\auto_misp.exe "C:\Program Files (x86)\ossec-agent\active-response\bin\"
Restart-Service WazuhSvc
```


### 2. Wazuh manager

1. Add the configuration from [`config/ossec.conf.snippet`](config/ossec.conf.snippet) to `/var/ossec/etc/ossec.conf`
2. Add the rules from [`config/local_rules.xml`](config/local_rules.xml) to `/var/ossec/etc/rules/local_rules.xml`
3. Restart the manager:
   ```bash
   sudo service wazuh-manager restart
   ```

> The rules depend on parent rule `100622` (the MISP integration rule), so the MISP ↔ Wazuh integration must already be in place.

##  Testing:

1. Open the Wazuh daworflowshboard → **Threat Intelligence → Threat Hunting → Events**
2. On the Windows endpoint, trigger a MISP-listed domain:
   ```powershell
   ping office.oiqezet.com
   ```
3. Verify the response:
   ```powershell
   Get-Content "C:\Program Files (x86)\ossec-agent\active-response\active-responses.log" -Tail 20
   Select-String "office.oiqezet.com" C:\Windows\System32\drivers\etc\hosts
   ```

Expected: the alert appears in Wazuh, the log shows a successful execution, and the domain resolves to `0.0.0.0`.

## Lab Walkthrough & Evidence:

Screenshots captured during the lab, in the order the workflow runs.

### 1️⃣ Building the executable with PyInstaller

<a href="docs/screenshots/01-pyinstaller-build.png"><img src="docs/screenshots/01-pyinstaller-build.png" alt="PyInstaller build output in PowerShell" width="100%"></a>

The script was compiled from an elevated PowerShell session inside the agent's `active-response\bin` folder:

```powershell
pyinstaller.exe --onefile -w auto_misp.py
```

What the output shows:

| Phase | What happens |
|---|---|
| **Environment check** | PyInstaller 6.11.1 on Python 3.13.1 / Windows 10 is detected, and a `auto_misp.spec` build recipe is written |
| **Analysis** | PyInstaller scans the script, builds the module dependency graph, runs its hooks and collects the required DLLs and libraries |
| **PKG** | The script and its dependencies are bundled into a single archive (`auto_misp.pkg`) |
| **EXE** | The Windows bootloader is copied, the manifest and icon are embedded and the archive is appended. The build ends with *"Building EXE … completed successfully"* |
| **Output** | `dist\auto_misp.exe`, a standalone executable that runs **without Python installed** |

> ⚠️ **Note on the warning at the top of the log:** PyInstaller states that running it as administrator is not necessary and that version 7.0 will block it. Build from a **normal (non-admin) terminal** and only elevate to copy the file into `Program Files (x86)` and restart `WazuhSvc`. Also prefer building in a separate working folder (as `build.ps1` does), so the `build/`, `dist/` and `.spec` files do not clutter the agent's `bin` directory.

### 2️⃣ Triggering the detection

<a href="docs/screenshots/02-ping-and-active-response-log.png"><img src="docs/screenshots/02-ping-and-active-response-log.png" alt="Ping to the malicious domain and the active-responses.log content" width="100%"></a>

The endpoint queries a domain that MISP lists as an IoC:

```powershell
ping office.oiqezet.com
```

The ping does not succeed ("could not find host"): the domain is no longer reachable from this machine. The log excerpt below the command is the actual proof of mitigation.

After restarting the Wazuh agent (so the new executable is loaded), `active-responses.log` records the full execution:

```text
2025-01-29 03:49:42.016302 - Active response started
2025-01-29 03:52:07.537202 - Raw input received: {"version":1,"origin":{"name":"node01","module":"wazuh-execd"}, ... }
2025-01-29 03:52:07.538840 - Parsed MISP data - Type: domain, Value: office.oiqezet.com
2025-01-29 03:52:07.541114 - Successfully blocked domain: office.oiqezet.com
2025-01-29 03:52:07.541721 - Active response completed.
```

How to read it:

1. **Active response started**: `wazuh-execd` launched `auto_misp.exe`.
2. **Raw input received**: the Wazuh manager's JSON alert arrived on `stdin` (`"command":"add"`).
3. **Parsed MISP data**: the script extracted the IoC type (`domain`) and value (`office.oiqezet.com`).
4. **Successfully blocked domain**: the sinkhole entry was written to the `hosts` file.
5. **Active response completed**: clean exit. From parsing to completion took roughly **4 ms**.

The same flow applies to IP addresses (firewall rule) and SHA256 hashes (file removal).

### 3️⃣ Alert in the Wazuh dashboard

<a href="docs/screenshots/03-wazuh-dashboard-alert.png"><img src="docs/screenshots/03-wazuh-dashboard-alert.png" alt="Wazuh Threat Hunting events showing the MISP alert" width="100%"></a>

In **Threat Hunting → Events**, the highlighted top row is the custom rule firing:

- **Description:** `MISP - Detected malicious domain: office.oiqezet.com`
- **Rule level:** 12, **rule ID:** 200003

The surrounding events give the full picture of what happened on the endpoint:

- **Sysmon Event 22 (DNS query)**: the DNS lookup caused by the `ping`, which is what Wazuh correlates with the MISP IoC.
- **Sysmon Events 1, 10 and 7**: process creation, process access and image load around the execution.
- **Highlighted lower rows**: `auto_misp.exe` loading runtime DLLs from a `_MEI…` folder in `C:\Windows\Temp`. This is normal behavior for a `--onefile` PyInstaller executable, which unpacks itself to a temporary folder at launch. It is worth knowing because security rules can flag it as *"executable loaded from the Temp directory"*, so expect (and tune for) this kind of alert.

### 4️⃣ The threat intelligence source (MISP)

<a href="docs/screenshots/04-misp-events.png"><img src="docs/screenshots/04-misp-events.png" alt="MISP events list" width="100%"></a>

The MISP instance holds the events and attributes (IP, domain, SHA256 IoCs) that feed the Wazuh integration. Reviewing events here is also how additional use cases can be explored: the same pipeline blocks IPs and deletes files when the matching IoC types are detected.


## 👤 Author:

**Zakaria MAARAK**: [GitHub](https://github.com/ZakariaMAARAK) · [LinkedIn](www.linkedin.com/in/zakaria-maarak)
