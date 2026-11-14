# 🛡️ **Automated Threat Mitigation**: MISP + Wazuh + Python 🛡️

> This project allows to simultaneously neutralizes IPs, domains and SHA256 hashes via a standalone executable (.exe) independent of the Python environment.  Wazuh consumes **MISP** threat intelligence and a custom Python script blocks malicious IPs, redirect malicious domains and purges malicious files on Windows endpoints with no manual intervention.

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
- **A custom Python script** (`misp-ar.py`), then it will be compiled to `.exe` via PyInstaller, that executes the mitigation on the endpoint

  

| IoC type (MISP) | Automated action | Mechanism |
|---|---|---|
| `ip-src` | Block inbound traffic | Windows Firewall rule via `netsh` |
| `Domain` | Sinkhole the domain | Redirect to `0.0.0.0` in the `hosts` file |
| `SHA256` | Delete the malicious file | `os.remove(file_path)` on the detected path |

Every action and error is written to an audit log (`active-responses.log`).


---


## Tools needed :

• Wazuh manager

• Wazuh agent (must be installed on the Windows Endpoint)

• MISP

• Python

• PyInstaller

• PowerShell

## Workflow :

<img width="3960" height="1078" alt="image" src="https://github.com/user-attachments/assets/d1dceeab-b1c0-4c0e-a9ed-40e7bc3ebfc4" />

The diagram covers both the **build/deploy pipeline** (Python script → PyInstaller → `.exe` → agent) and the **runtime detection/response flow**.



##  Project Files :

| File | Description |
|---|---|
| [`src/misp-ar.py`](src/misp-ar.py) | Active Response script (source code) |
| [`config/local_rules.xml`](config/local_rules.xml) | Custom Wazuh rules `200003` (domain) and `200004` (SHA256) |
| [`config/ossec.conf`](config/ossec.conf) | Wazuh manager `<command>` and `<active-response>` configuration |


###  Wazuh manager

1. Add the configuration from [`config/ossec.conf`](config/ossec.conf) to `/var/ossec/etc/ossec.conf`
2. Add the rules from [`config/local_rules.xml`](config/local_rules.xml) to `/var/ossec/etc/rules/local_rules.xml`
3. Restart the manager:
   ```bash
   sudo service wazuh-manager restart
   ```

> NB: After each configuration change to the files, do not forget to restart the wazuh manager service for the changes to take effect.

##  Testing :

1. Open the Wazuh daworflowshboard → **Threat Intelligence → Threat Hunting → Events**
2. On the Windows endpoint, trigger a MISP-listed domain:
   ```powershell
   ping office.oiqezet.com
   ```
3. Verify the response :
   ```powershell
   Get-Content "C:\Program Files (x86)\ossec-agent\active-response\active-responses.log" -Tail 20
   Select-String "office.oiqezet.com" C:\Windows\System32\drivers\etc\hosts
   ```

Expected: the alert appears in Wazuh, the log shows a successful execution, and the domain resolves to `0.0.0.0`.

## Lab Walkthrough & Setup :

### 1️⃣ Endpoint (Windows agent): Building the executable with PyInstaller

> 💡 [PyInstaller](https://pyinstaller.org) is a Python package used to convert Python scripts (`.py` files) into standalone executable files (`.exe` for Windows). This is essential for running Python scripts in environments where **Python itself may not be installed**.


```powershell
pip install -r requirements-build.txt

# --onefile: single standalone .exe   |   -w: no console window
pyinstaller.exe --onefile -w --name misp-ar src\misp-ar.py

```

<img width="1822" height="848" alt="22222" src="https://github.com/user-attachments/assets/16f944e0-5b62-4a62-85bd-606b77ab06c2" />
<img width="1370" height="412" alt="3333333" src="https://github.com/user-attachments/assets/f382aa05-57bf-4f79-adb7-4c5970e96ede" />

The script was compiled from an elevated PowerShell session inside the agent's `active-response\bin` folder:

```powershell
pyinstaller.exe --onefile -w misp-ar.py
```

What the output shows:

| Phase | What happens |
|---|---|
| **Environment check** | PyInstaller 6.11.1 on Python 3.13.1 / Windows 10 is detected, and a `misp-ar.spec` build recipe is written |
| **Analysis** | PyInstaller scans the script, builds the module dependency graph, runs its hooks and collects the required DLLs and libraries |
| **PKG** | The script and its dependencies are bundled into a single archive (`misp-ar.pkg`) |
| **EXE** | The Windows bootloader is copied, the manifest and icon are embedded and the archive is appended. The build ends with *"Building EXE … completed successfully"* |
| **Output** | `dist\misp-ar.exe`, a standalone executable that runs **without Python installed** |

> ⚠️ **Warning at the top of the log:** PyInstaller states that running it as administrator is not necessary and that version 7.0 will block it. Build from a **normal (non-admin) terminal** and only elevate to copy the file into `Program Files (x86)` and restart `WazuhSvc`. Also prefer building in a separate working folder (as `build.ps1` does), so the `build/`, `dist/` and `.spec` files do not clutter the agent's `bin` directory.

### 2️⃣ Triggering the detection

The endpoint queries a domain that MISP lists as an IoC:

```powershell
ping office.oiqezet.com
```

The ping does not succeed ("could not find host"): the domain is no longer reachable from this machine. The log excerpt below the command is the actual proof of mitigation.

<img width="1139" height="55" alt="image" src="https://github.com/user-attachments/assets/857b4d2d-0aa2-4f62-8d4b-3d8ac9916950" />

After restarting the Wazuh agent ----> the new executable is loaded ----> `active-responses.log` records the execution :


<img width="883" height="71" alt="image" src="https://github.com/user-attachments/assets/aca6a3ec-8001-48c1-8763-c75705c08d89" />


How to read it:

1. **Active response started**: `wazuh-execd` launched `misp-ar.exe`.
2. **Raw input received**: the Wazuh manager's JSON alert arrived on `stdin` (`"command":"add"`).
3. **Parsed MISP data**: the script extracted the IoC type (`domain`) and value (`office.oiqezet.com`).
4. **Successfully blocked domain**: the sinkhole entry was written to the `hosts` file.
5. **Active response completed**: clean exit. From parsing to completion took roughly **4 ms**.

The same flow applies to IP addresses (firewall rule) and SHA256 hashes (file removal).

### 3️⃣ Alert in the Wazuh dashboard

<img width="1372" height="342" alt="44444" src="https://github.com/user-attachments/assets/3b26c431-89d2-4c51-abaf-df3109cca614" />

In **Threat Hunting → Events**, the highlighted top row is the custom rule firing:

- **Description:** `MISP - Detected malicious domain: office.oiqezet.com`
- **Rule level:** 12, **rule ID:** 200003

The surrounding events give the full picture of what happened on the endpoint:

- **Sysmon Event 22 (DNS query)**: the DNS lookup caused by the `ping`, which is what Wazuh correlates with the MISP IoC.
- **Sysmon Events 1, 10 and 7**: process creation, process access and image load around the execution.
- **Highlighted lower rows**: `misp-ar.exe` loading runtime DLLs from a `_MEI…` folder in `C:\Windows\Temp`. This is normal behavior for a `--onefile` PyInstaller executable, which unpacks itself to a temporary folder at launch. It is worth knowing because security rules can flag it as *"executable loaded from the Temp directory"*, so expect (and tune for) this kind of alert.

### 4️⃣ The threat intelligence source (MISP)

<img width="1807" height="830" alt="1111111" src="https://github.com/user-attachments/assets/54d91d12-6a0a-4053-a2f9-de320c068442" />

The MISP instance holds the events and attributes (IP, domain, SHA256) that feed the Wazuh integration. Reviewing events here is also how additional use cases can be explored: the same pipeline blocks IPs and deletes files when the matching IoC types are detected.


---



Authored by **Zakaria MAARAK**: [GitHub](https://github.com/ZakariaMAARAK) · [LinkedIn](https://linkedin.com/in/zakaria-maarak)
