# DETCONNECT NOC Monitor

A starter Network Operations Center monitoring project for an ISP environment. Designed for DETCONNECT / Digital Essentials Trading and adaptable to MikroTik RouterOS v7, BGP edge routers, switches, and GPON OLTs.

## Features
- Web dashboard with device status, latency, uptime, and recent events
- ICMP reachability checks
- Optional SNMP v2c interface/CPU/RAM metrics (depends on device MIB support)
- Telegram alert notifications for DOWN/UP transitions
- YAML inventory configuration
- SQLite event history
- Docker deployment and local Python deployment
- No router configuration changes are performed by this application

## Requirements
- Python 3.11+
- Network access from the monitoring host to managed devices
- `ping` utility available on the host/container
- Optional: SNMP enabled on devices and `pysnmp` installed
- Optional: Telegram bot token and chat ID

## Quick start
```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# Linux:
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```
Open http://127.0.0.1:8080

Edit `config/devices.yaml` to add your devices. Start with management IPs only; do not expose the dashboard directly to the public internet.

## Docker
```bash
docker compose up --build -d
```
Open http://SERVER-IP:8080 on a trusted management network.

## Configuration
`config/devices.yaml`:
```yaml
poll_interval_seconds: 30
timeout_seconds: 2
devices:
  - name: DETCONNECT-CCR2216-EDGE
    host: 192.0.2.1
    role: MikroTik BGP Edge
    site: Main POP
    enabled: true
    snmp:
      enabled: false
      community_env: SNMP_COMMUNITY
```
Replace documentation IPs with your actual management IPs. Use unique device names.

## Telegram alerts
1. Create a Telegram bot and obtain its token.
2. Obtain the target chat ID.
3. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`.
4. Restart the app.

Never commit `.env`, credentials, or real management IP inventory to a public repository.

## SNMP
SNMP polling is optional and disabled by default. Set `snmp.enabled: true` for a device and set `SNMP_COMMUNITY` in `.env`. Use read-only SNMP communities, restrict allowed managers by ACL, and prefer SNMPv3 where supported. This starter provides basic system uptime and interface traffic data when the device exposes standard IF-MIB objects. Device-specific CPU/RAM OIDs vary by vendor and model.

## Production hardening checklist
- Put the dashboard behind a VPN or management VLAN and firewall allowlist.
- Add authentication / SSO and HTTPS before multi-user or production exposure.
- Use SNMPv3 where possible; never use write access.
- Use a dedicated least-privilege monitoring account.
- Back up `data/` and the YAML inventory.
- Tune polling intervals to avoid overloading routers/OLT control planes.
- Test alerts and recovery behavior before relying on them operationally.
- Treat ICMP failure as a reachability alarm, not proof of a fiber cut; correlate OLT/PON/ONU and upstream signals.

## Roadmap
- RouterOS API adapter for BGP peer state and resource metrics
- BGP session/route validation for IPv4 and IPv6
- OLT vendor adapters for PON/ONU/LOS metrics
- Grafana/Prometheus integration
- Role-based authentication, maintenance windows, escalation policies
- Topology view and subscriber/PPPoE event integration

## Repository layout
```text
app.py
monitor.py
config/devices.yaml
templates/index.html
static/style.css
requirements.txt
Dockerfile
docker-compose.yml
.env.example
```

## License
MIT
