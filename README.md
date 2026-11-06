# Automated Threat Detection & Response using MISP & Wazuh

---

<p align="center">
  <!-- Row 1 -->
  <img src="https://img.shields.io/badge/MISP-Threat%20Intelligence-0078D4?style=for-the-badge&logo=security-scorecard&logoColor=white" alt="MISP - Threat Intelligence" />
  <img src="https://img.shields.io/badge/Wazuh-SIEM-008080?style=for-the-badge&logo=wazuh&logoColor=white" alt="Wazuh - SIEM" />
  <img src="https://img.shields.io/badge/Python-Automation-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python - Automation" />
  <br/>
  <!-- Row 2 -->
  <img src="https://img.shields.io/badge/Windows-Endpoint%20Security-0078D7?style=for-the-badge&logo=windows&logoColor=white" alt="Windows - Endpoint Security" />
  <img src="https://img.shields.io/badge/PowerShell-Scripting-5391FE?style=for-the-badge&logo=powershell&logoColor=white" alt="PowerShell - Scripting" />
  <img src="https://img.shields.io/badge/PyInstaller-Executable%20Builds-555555?style=for-the-badge&logo=python&logoColor=white" alt="PyInstaller - Executable Builds" />
  <br/>
  <!-- Row 3 -->
  <img src="https://img.shields.io/badge/Active%20Response-Automation-28a745?style=for-the-badge&logo=githubactions&logoColor=white" alt="Active Response - Automation" />
  <img src="https://img.shields.io/badge/Windows%20Firewall-Netsh-dc3545?style=for-the-badge&logo=windows-terminal&logoColor=white" alt="Windows Firewall - Netsh" />
  <img src="https://img.shields.io/badge/IOC-IP%20%7C%20Domain%20%7C%20SHA256-fd7e14?style=for-the-badge&logo=target&logoColor=white" alt="IOC - IP | Domain | SHA256" />
</p>

---

## Overview :

This project aims to implement an automated cybersecurity defense solution by integrating **MISP (Malware Information Sharing Platform)** with **Wazuh SIEM Active Response**.

The solution leverages Threat Intelligence Indicators of Compromise (IOCs), such as malicious IP addresses, domains, and SHA256 hashes, to trigger automated mitigation actions on monitored Windows endpoints.

A custom Python script processes security alerts received from the Wazuh Manager and executes the corresponding response action according to the detected IOC type.

The main objective is to reduce manual intervention during incident response and improve the speed of threat mitigation within a SOC environment.

## Conception :


<img width="1057" height="417" alt="socconceptioou" src="https://github.com/user-attachments/assets/0f2102f1-5c0c-4e68-ab11-d73c02c8f1a2" />



The solution is organized into three main layers:

**1. Threat Intelligence & Detection Layer**

- MISP platform for managing and sharing threat intelligence.
- IOC identification (IP addresses, domains, SHA256 hashes).
- Wazuh Manager for security event processing.
- Custom Wazuh detection rules for MISP-related alerts.

**2. Windows Endpoint & Execution Layer**

- Wazuh Agent installed on the Windows endpoint.
- Active Response service.
- Custom Python script (`misp-ar.py`).
- PyInstaller to package the Python script into a standalone Windows executable.

**3. Automated Threat Mitigation Layer**

Depending on the detected IOC type, the script performs the following actions:

| IOC Type | Automated Action |
|---|---|
| `ip-src` | Block the IP address using Windows Firewall |
| `domain` | Block the domain through the Windows Hosts file |
| `sha256` | Identify and remove the matching malicious file |
| All actions | Generate operational logs |

## Technologies and frameworks :

- MISP (Malware Information Sharing Platform)
- Wazuh SIEM
- Wazuh Active Response
- Python
- PyInstaller
- Windows Firewall (Netsh)
- Windows Hosts File
- JSON
- PowerShell
- Windows Endpoint Security

## Getting started :

### Prerequisites :

Before starting the implementation, make sure you have:

- A Linux environment hosting the Wazuh Manager.
- MISP configured with threat intelligence indicators.
- A Windows machine with Wazuh Agent installed.
- Python installed on the Windows machine used to build the executable.
- Administrator privileges on the Windows endpoint.
- Network connectivity between the Wazuh Manager and Agent.

## Steps to configure the solution :

### STEP 1 : Configure MISP Threat Intelligence

Access your MISP platform and configure the threat intelligence indicators that will be used for testing.

The lab focuses on three types of Indicators of Compromise (IOCs):

- Malicious IP addresses.
- Malicious domain names.
- Malicious file SHA256 hashes.

These indicators will be used to generate security events processed by Wazuh.

### STEP 2 : Configure Wazuh Detection Rules

On the Wazuh Manager, navigate to the local rules configuration file:

`/var/ossec/etc/rules/local_rules.xml`

Create custom rules to identify MISP-related events according to their IOC types.

The implemented rules include:

- **Rule ID 200003:** Detect malicious domains using the `misp.type` field.
- **Rule ID 200004:** Detect malicious SHA256 hashes using the `misp.type` field.

The rules are associated with the MISP parent detection rule (100622).

Example rule configuration:

```xml
<group name="misp,active-response,">

  <rule id="200003" level="12">
    <if_sid>100622</if_sid>
    <field name="misp.type">^domain$</field>
    <description>MISP - Detected malicious domain: $(misp.value)</description>
  </rule>

  <rule id="200004" level="12">
    <if_sid>100622</if_sid>
    <field name="misp.type">^sha256$</field>
    <description>MISP - Detected malicious file hash (SHA256): $(misp.value)</description>
  </rule>

</group>
```

**Note:** Adapt the parent rule ID and field names to your actual MISP integration and Wazuh alert structure.

### STEP 3 : Develop the Python Active Response Script

On the Windows endpoint, navigate to:

`C:\Program Files (x86)\ossec-agent\active-response\bin`

Create a Python script named:

`misp-ar.py`

The script processes JSON alerts received through standard input (`sys.stdin`) and extracts the IOC information.

The implementation contains the following functions:

**1. write_log()**

Records execution results, successful actions, and errors in:

`C:\Program Files (x86)\ossec-agent\active-response\active-responses.log`

**2. block_ip()**

Uses the Windows `netsh` command to create a Windows Firewall rule that blocks traffic from a specified malicious IP address.

**3. block_domain()**

Modifies the Windows Hosts file:

`C:\Windows\System32\drivers\etc\hosts`

The malicious domain is redirected to `0.0.0.0` to prevent normal name resolution to its legitimate destination.

**4. delete_file()**

Handles malicious file removal by checking the file path and deleting the identified file.

The SHA256 hash must be verified against the actual file before deletion.

**5. main()**

Processes the JSON input, identifies the IOC type and value, and executes the appropriate mitigation function.

### STEP 4 : Package the Python Script using PyInstaller

To execute the script on Windows without requiring a Python installation on the endpoint, package it into a standalone executable.

Install PyInstaller:

```powershell
pip install pyinstaller
```

Generate the executable:

```powershell
pyinstaller --onefile -w misp-ar.py
```

After the build process, the executable will be generated inside the `dist` directory.

Copy `misp-ar.exe` into:

`C:\Program Files (x86)\ossec-agent\active-response\bin`

### STEP 5 : Configure Wazuh Active Response

On the Wazuh Manager, edit:

`/var/ossec/etc/ossec.conf`

Define the custom command used to execute the Windows response script:

```xml
<command>
  <name>misp-active-response</name>
  <executable>misp-ar.exe</executable>
  <timeout_allowed>yes</timeout_allowed>
</command>
```

Associate the command with the corresponding detection rules:

```xml
<active-response>
  <command>misp-active-response</command>
  <location>defined-agent-location</location>
  <rules_id>200003,200004</rules_id>
  <timeout>10</timeout>
</active-response>
```

**Important:** Configure the appropriate agent execution location and response scope for your environment. Ensure the executable is deployed on the endpoint where the response must run.

### STEP 6 : Restart Wazuh Services

On the Windows endpoint, restart the Wazuh Agent using PowerShell:

```powershell
Restart-Service WazuhSvc
```

On the Wazuh Manager, restart the service:

```bash
sudo systemctl restart wazuh-manager
```

Verify that both services are running correctly before proceeding with the tests.

### STEP 7 : Test and Validate Automated Responses

Access the Wazuh Dashboard through your browser:

`https://<WAZUH_MANAGER_IP>`

Navigate to:

**Threat Intelligence → Threat Hunting → Events**

Generate a controlled test event using a test domain configured in your MISP integration.

Example:

```powershell
ping office.oiqezet.com
```

This command can generate a DNS lookup event if the domain is resolved through the configured monitoring environment.

Verify the following:

- The corresponding MISP-related alert is generated.
- Wazuh identifies the matching custom detection rule.
- Active Response is triggered on the Windows endpoint.
- The appropriate mitigation action is executed.
- The execution result is recorded in `active-responses.log`.

Repeat the validation process for each supported IOC type.

**Testing note:** Use controlled test indicators and harmless test files in an isolated lab. A successful ping command alone does not prove that every mitigation action has executed successfully.

## Expected Results :

The implementation demonstrates the ability to automate several threat mitigation operations:

- Detection of malicious indicators through threat intelligence.
- Automated response triggered by Wazuh SIEM.
- IP address blocking through Windows Firewall.
- Domain blocking through the Windows Hosts file.
- SHA256-based malicious file identification and removal.
- Operational logging for incident response traceability.

## Security Considerations :

- Active Response scripts must run with appropriate privileges.
- Validate IOC values before executing system commands.
- Verify file hashes before deleting files.
- Avoid using real malicious indicators on production systems.
- Prevent duplicate firewall rules and Hosts file entries.
- Monitor automated actions to avoid false positives and unintended service disruptions.

## Learning Outcomes :

Through this hands-on lab, I gained practical experience in:

- Threat Intelligence and IOC management.
- SIEM integration and security event monitoring.
- Wazuh Active Response configuration.
- Python-based security automation.
- Windows Firewall and endpoint security.
- Automated incident response.
- Security event analysis and operational logging.

---

**Project Category:** Cybersecurity | SOC Operations | Threat Intelligence | Security Automation

**Author:** Zakaria MAARAK
