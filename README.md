# OpenStack Load Balancer Tree View

[![PyPI version](https://img.shields.io/pypi/v/openstack-lb-treeview)](https://pypi.org/project/openstack-lb-treeview/)
![License](https://img.shields.io/pypi/l/openstack-lb-treeview)
![Python versions](https://img.shields.io/pypi/pyversions/openstack-lb-treeview)

A Python script that displays a tree view of all loadbalancers in an OpenStack project, showing pools and members in a hierarchical structure.

## Features

- Displays loadbalancers as root nodes
- Shows pools as children of loadbalancers
- Shows members as children of pools
- Shows `provisioning_status` and `operating_status` for load balancers, pools, and members
- Shows a per-pool member operating-status summary (e.g. `13 ERROR - 3 ONLINE - 16 TOTAL`)
- Highlights members with `provisioning_status != ACTIVE` (yellow/bold)
- Displays members with `operating_status != ONLINE` in red
- **Single LB**: Show the tree for one load balancer by name or ID (`--lb`)
- **Filter mode**: Show only problematic members (not ACTIVE/ONLINE) and pools with no members
- **Collapse mode**: Show pools with member status summary, without listing individual members

## Installation

### Install globally via pip

Install directly from PyPi:

```bash
pip install openstack-lb-treeview
```

After installation, the `openstack-lb-treeview` command will be available globally.

### Set up OpenStack credentials

Set up your OpenStack credentials. You can either:
- Set environment variables (OS_AUTH_URL, OS_USERNAME, OS_PASSWORD, etc.)
- Use a `clouds.yaml` file in `~/.config/openstack/` or `/etc/openstack/`

## Usage

After installation, use the `openstack-lb-treeview` command:

Basic usage (uses environment variables for authentication):
```bash
openstack-lb-treeview
```

Specify a cloud from clouds.yaml:
```bash
openstack-lb-treeview --cloud mycloud
```

Filter by project ID:
```bash
openstack-lb-treeview --project-id <project-id>
```

Single load balancer by name or ID:
```bash
openstack-lb-treeview --lb my-loadbalancer
openstack-lb-treeview --lb abc123-def456-...
```

Filter mode (only show problematic members and empty pools):
```bash
openstack-lb-treeview --filter
openstack-lb-treeview --lb my-loadbalancer --filter
```

Collapse mode (pool summary only, no individual members):
```bash
openstack-lb-treeview --collapse
```

Combined filter and collapse mode (show only load balancers with operating_status != 'ONLINE'):
```bash
openstack-lb-treeview --filter --collapse
```

### Development Usage

If running from source without installation:
```bash
python -m openstack_lb_treeview.lb_treeview
```

Or directly:
```bash
python openstack_lb_treeview/lb_treeview.py
```

## Example Output

Normal mode:
```
📦 my-loadbalancer (ID: abc123...) (provisioning: ACTIVE | operating: ONLINE)
  ├─ 🏊 pool-1 (ID: def456...) (provisioning: ACTIVE | operating: DEGRADED) | 1 OFFLINE - 1 ONLINE - 2 TOTAL
  │  ├─ 👤 member-1 (provisioning: ACTIVE | operating: ONLINE)
  │  └─ 👤 member-2 (provisioning: PENDING_CREATE | operating: OFFLINE)
  └─ 🏊 pool-2 (ID: ghi789...) (provisioning: ACTIVE | operating: ONLINE) | 1 ONLINE - 1 TOTAL
     └─ 👤 member-3 (provisioning: ACTIVE | operating: ONLINE)
```

Filter mode (`--filter`):
```
📦 my-loadbalancer (ID: abc123...) (provisioning: ACTIVE | operating: DEGRADED)
  ├─ 🏊 pool-1 (ID: def456...) (provisioning: ACTIVE | operating: DEGRADED) | 1 OFFLINE - 1 ONLINE - 2 TOTAL
  │  └─ 👤 member-2 (provisioning: PENDING_CREATE | operating: OFFLINE)
  └─ 🏊 pool-3 (ID: xyz789...) (provisioning: ACTIVE | operating: OFFLINE) | 0 TOTAL
     └─ No members
```

In filter mode, only pools with problematic members (not ACTIVE or not ONLINE) or pools with no members are shown. The pool summary still counts all members.

Collapse mode (`--collapse`):
```
📦 my-loadbalancer (ID: abc123...) (provisioning: ACTIVE | operating: ONLINE)
  ├─ 🏊 pool-1 (ID: def456...) (provisioning: ACTIVE | operating: DEGRADED) | 1 OFFLINE - 1 ONLINE - 2 TOTAL
  └─ 🏊 pool-2 (ID: ghi789...) (provisioning: ACTIVE | operating: ONLINE) | 1 ONLINE - 1 TOTAL
```

In collapse mode, pools are shown with status and member summary, but individual members are not listed.

Combined filter and collapse mode (`--filter --collapse`):
```
📦 my-loadbalancer (ID: abc123...) (provisioning: ACTIVE | operating: DEGRADED)
  ├─ 🏊 pool-1 (ID: def456...) (provisioning: ACTIVE | operating: DEGRADED) | 1 OFFLINE - 1 ONLINE - 2 TOTAL
  └─ 🏊 pool-2 (ID: ghi789...) (provisioning: ACTIVE | operating: ONLINE) | 1 ONLINE - 1 TOTAL
```

When both `--filter` and `--collapse` are used together, only load balancers with `operating_status != 'ONLINE'` are displayed. This is useful for quickly identifying load balancers that are not in an ONLINE state.

## Requirements

- Python 3.6+
- openstacksdk
- OpenStack credentials with appropriate permissions

