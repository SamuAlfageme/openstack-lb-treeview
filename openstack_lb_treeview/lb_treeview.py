#!/usr/bin/env python3
"""
OpenStack Load Balancer Tree View Script

Displays a tree view of all loadbalancers in a project, showing:
- Loadbalancers as root nodes
- Pools as children of loadbalancers
- Members as children of pools

Highlights:
- Members with provisioning_status != ACTIVE are highlighted
- Members with operating_status != ONLINE are displayed in red
"""

import sys
import argparse
from collections import Counter
from openstack import connection
from openstack.exceptions import OpenStackCloudException


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    UNDERLINE = '\033[4m'


# Preferred display order for member operating_status summary
OPERATING_STATUS_ORDER = (
    'ERROR',
    'DEGRADED',
    'OFFLINE',
    'DRAINING',
    'NO_MONITOR',
    'ONLINE',
)


def get_connection():
    """Create OpenStack connection using environment variables or clouds.yaml"""
    try:
        conn = connection.Connection(cloud='envvars')
        return conn
    except Exception as e:
        print(f"Error connecting to OpenStack: {e}")
        print("Make sure you have OpenStack credentials set in environment variables")
        print("or configured in clouds.yaml")
        sys.exit(1)


def resource_attr(obj, key, default='UNKNOWN'):
    """Read an attribute from an SDK object or dict."""
    if hasattr(obj, key) and not isinstance(obj, dict):
        value = getattr(obj, key, None)
    else:
        value = obj.get(key) if isinstance(obj, dict) else None
    return value if value is not None else default


def member_to_dict(member):
    """Normalize a member SDK object or dict to a plain dict."""
    if hasattr(member, 'name') and not isinstance(member, dict):
        return {
            'id': member.id,
            'name': member.name,
            'provisioning_status': getattr(member, 'provisioning_status', 'UNKNOWN'),
            'operating_status': getattr(member, 'operating_status', 'UNKNOWN'),
        }
    return member


def is_member_problematic(member):
    """Check if a member has issues (not ACTIVE or not ONLINE)"""
    prov_status = member.get('provisioning_status', 'UNKNOWN')
    oper_status = member.get('operating_status', 'UNKNOWN')
    return prov_status != 'ACTIVE' or oper_status != 'ONLINE'


def format_status_pair(prov_status, oper_status):
    """Format provisioning/operating status with highlighting."""
    if prov_status != 'ACTIVE':
        prov_display = f"{Colors.YELLOW}{Colors.BOLD}{prov_status}{Colors.RESET}"
    else:
        prov_display = prov_status

    if oper_status != 'ONLINE':
        oper_display = f"{Colors.RED}{oper_status}{Colors.RESET}"
    else:
        oper_display = oper_status

    return f"provisioning: {prov_display} | operating: {oper_display}"


def format_member_status(member):
    """Format member with appropriate highlighting based on status"""
    name = member.get('name', member.get('id', 'N/A'))
    prov_status = member.get('provisioning_status', 'UNKNOWN')
    oper_status = member.get('operating_status', 'UNKNOWN')
    return f"{name} ({format_status_pair(prov_status, oper_status)})"


def colorize_operating_status(status):
    """Color an operating_status label for the member summary."""
    if status == 'ONLINE':
        return status
    if status in ('ERROR', 'DEGRADED', 'OFFLINE'):
        return f"{Colors.RED}{status}{Colors.RESET}"
    if status in ('DRAINING', 'NO_MONITOR', 'UNKNOWN'):
        return f"{Colors.YELLOW}{status}{Colors.RESET}"
    return f"{Colors.YELLOW}{status}{Colors.RESET}"


def format_member_summary(members):
    """Build a compact operating_status breakdown for pool members.

    Example: 13 ERROR - 3 DEGRADED - 4 OFFLINE - 3 ONLINE - 23 TOTAL
    """
    counts = Counter(
        m.get('operating_status', 'UNKNOWN') or 'UNKNOWN' for m in members
    )
    total = sum(counts.values())
    parts = []

    for status in OPERATING_STATUS_ORDER:
        count = counts.pop(status, 0)
        if count:
            parts.append(f"{count} {colorize_operating_status(status)}")

    for status in sorted(counts):
        parts.append(f"{counts[status]} {colorize_operating_status(status)}")

    parts.append(f"{Colors.BOLD}{total} TOTAL{Colors.RESET}")
    return " - ".join(parts)


def format_lb_line(lb_name, lb_id, prov_status, oper_status):
    """Format the load balancer header line."""
    status = format_status_pair(prov_status, oper_status)
    return (
        f"{Colors.BOLD}{Colors.BLUE}📦 {lb_name}{Colors.RESET} "
        f"(ID: {lb_id}) ({status})"
    )


def format_pool_line(prefix, pool_name, pool_id, prov_status, oper_status, members=None):
    """Format a pool line with status and optional member summary."""
    status = format_status_pair(prov_status, oper_status)
    line = (
        f"{prefix} {Colors.GREEN}🏊 {pool_name}{Colors.RESET} "
        f"(ID: {pool_id}) ({status})"
    )
    if members is not None:
        line += f" | {format_member_summary(members)}"
    return line


def resolve_loadbalancers(conn, project_id=None, lb_name_or_id=None):
    """Resolve load balancers to display.

    Args:
        conn: OpenStack connection object
        project_id: Optional project ID to filter by
        lb_name_or_id: Optional load balancer name or ID to show a single LB

    Returns:
        List of load balancer objects
    """
    if lb_name_or_id:
        kwargs = {}
        if project_id:
            kwargs['project_id'] = project_id

        # Try direct ID fetch first (fast path for UUIDs)
        try:
            lb = conn.load_balancer.get_load_balancer(lb_name_or_id)
            if lb:
                return [lb]
        except (OpenStackCloudException, Exception):
            pass

        # Fall back to name / name_or_id search via the SDK finder
        try:
            lb = conn.load_balancer.find_load_balancer(
                lb_name_or_id, ignore_missing=True, **kwargs
            )
            if lb:
                return [lb]
        except (OpenStackCloudException, Exception):
            pass

        # Last resort: list and match by name (handles ambiguous/duplicate names)
        list_kwargs = dict(kwargs)
        list_kwargs['name'] = lb_name_or_id
        matches = list(conn.load_balancer.load_balancers(**list_kwargs))
        if len(matches) == 1:
            return matches
        if len(matches) > 1:
            print(
                f"{Colors.RED}Error: Multiple load balancers named "
                f"'{lb_name_or_id}'. Use --lb <id> instead.{Colors.RESET}"
            )
            for match in matches:
                if hasattr(match, 'id'):
                    match_id = match.id
                    match_project = getattr(match, 'project_id', '?')
                else:
                    match_id = match.get('id', '?')
                    match_project = match.get('project_id', '?')
                print(f"  - ID: {match_id} (project: {match_project})")
            first = matches[0]
            first_id = first.id if hasattr(first, 'id') else first.get('id', '<id>')
            print(f"Example: openstack-lb-treeview --lb {first_id}")
            sys.exit(1)

        print(
            f"{Colors.RED}Error: Load balancer '{lb_name_or_id}' not found.{Colors.RESET}"
        )
        print("Example: openstack-lb-treeview --lb <load-balancer-id-or-name>")
        sys.exit(1)

    if project_id:
        return list(conn.load_balancer.load_balancers(project_id=project_id))
    return list(conn.load_balancer.load_balancers())


def print_tree(conn, project_id=None, filter_mode=False, collapse_mode=False, lb_name_or_id=None):
    """Print tree view of loadbalancers, pools, and members

    Args:
        conn: OpenStack connection object
        project_id: Optional project ID to filter by
        filter_mode: If True, only show problematic members and pools with no members
        collapse_mode: If True, show pools (with member status summary) but not individual members
        lb_name_or_id: Optional load balancer name or ID to show a single LB
    """
    try:
        loadbalancers = resolve_loadbalancers(
            conn, project_id=project_id, lb_name_or_id=lb_name_or_id
        )

        if not loadbalancers:
            print("No loadbalancers found in the project.")
            return

        for lb in loadbalancers:
            lb_name = resource_attr(lb, 'name', None) or resource_attr(lb, 'id')
            lb_id = resource_attr(lb, 'id')
            lb_prov_status = resource_attr(lb, 'provisioning_status')
            lb_oper_status = resource_attr(lb, 'operating_status')

            # When both filter and collapse are enabled, filter by load balancer operating_status
            if filter_mode and collapse_mode:
                # Only show load balancers with operating_status != 'ONLINE'
                if lb_oper_status == 'ONLINE':
                    continue

            # Get pools for this loadbalancer
            try:
                pools = list(conn.load_balancer.pools(loadbalancer_id=lb_id))

                # Build (pool, all_members, display_members) entries.
                # all_members is used for the status summary; display_members for listing.
                prepared_pools = []
                for pool in pools:
                    pool_id = resource_attr(pool, 'id')

                    try:
                        all_members = [
                            member_to_dict(m)
                            for m in conn.load_balancer.members(pool=pool_id)
                        ]
                    except (OpenStackCloudException, Exception):
                        if filter_mode and not collapse_mode:
                            # Skip pools we cannot inspect in filter mode
                            continue
                        all_members = None

                    if collapse_mode:
                        display_members = None
                    elif filter_mode:
                        if all_members is None:
                            continue
                        problematic = [m for m in all_members if is_member_problematic(m)]
                        if len(all_members) > 0 and len(problematic) == 0:
                            continue
                        display_members = problematic
                    else:
                        display_members = all_members

                    prepared_pools.append((pool, all_members, display_members))

                if filter_mode and not collapse_mode and not prepared_pools:
                    continue

                print(format_lb_line(lb_name, lb_id, lb_prov_status, lb_oper_status))

                if not prepared_pools:
                    print(f"  └─ {Colors.BLUE}No pools{Colors.RESET}")
                    print()
                    continue

                for idx, (pool, all_members, display_members) in enumerate(prepared_pools):
                    pool_name = resource_attr(pool, 'name', None) or resource_attr(pool, 'id')
                    pool_id = resource_attr(pool, 'id')
                    pool_prov_status = resource_attr(pool, 'provisioning_status')
                    pool_oper_status = resource_attr(pool, 'operating_status')

                    is_last_pool = (idx == len(prepared_pools) - 1)
                    prefix = "  └─" if is_last_pool else "  ├─"
                    member_prefix = "     " if is_last_pool else "  │  "

                    print(
                        format_pool_line(
                            prefix,
                            pool_name,
                            pool_id,
                            pool_prov_status,
                            pool_oper_status,
                            members=all_members,
                        )
                    )

                    if collapse_mode:
                        continue

                    if display_members is None:
                        print(
                            f"{member_prefix}└─ "
                            f"{Colors.RED}Error fetching members{Colors.RESET}"
                        )
                        continue

                    if len(display_members) == 0:
                        print(f"{member_prefix}└─ {Colors.BLUE}No members{Colors.RESET}")
                        continue

                    for mem_idx, member in enumerate(display_members):
                        is_last_member = (mem_idx == len(display_members) - 1)
                        if is_last_pool:
                            member_connector = "     └─" if is_last_member else "     ├─"
                        else:
                            member_connector = "  │  └─" if is_last_member else "  │  ├─"

                        member_str = format_member_status(member)
                        print(f"{member_connector} {Colors.BOLD}👤{Colors.RESET} {member_str}")

            except (OpenStackCloudException, Exception) as e:
                if not filter_mode:
                    print(format_lb_line(lb_name, lb_id, lb_prov_status, lb_oper_status))
                    print(f"  └─ {Colors.RED}Error fetching pools: {e}{Colors.RESET}")
                    print()
                continue

            print()  # Empty line between loadbalancers

    except (OpenStackCloudException, Exception) as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Display a tree view of OpenStack loadbalancers, pools, and members',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  openstack-lb-treeview
  openstack-lb-treeview --lb my-loadbalancer
  openstack-lb-treeview --lb abc123-def456-...
  openstack-lb-treeview --lb my-loadbalancer --filter
  openstack-lb-treeview --lb my-loadbalancer --collapse
  openstack-lb-treeview --project-id <project-id>
  openstack-lb-treeview --cloud mycloud --filter --collapse
"""
    )
    parser.add_argument(
        '--lb',
        '--loadbalancer',
        dest='lb',
        metavar='NAME_OR_ID',
        help='Show tree view for a single load balancer (by name or ID)',
        default=None
    )
    parser.add_argument(
        '--project-id',
        help='Filter by specific project ID (optional)',
        default=None
    )
    parser.add_argument(
        '--cloud',
        help='Cloud name from clouds.yaml (default: envvars)',
        default='envvars'
    )
    parser.add_argument(
        '--filter',
        action='store_true',
        help='Filter mode: only show problematic members (not ACTIVE/ONLINE) and pools with no members'
    )
    parser.add_argument(
        '--collapse',
        action='store_true',
        help='Collapse mode: show pools with member status summary, without listing individual members'
    )

    args = parser.parse_args()

    # Create connection
    try:
        if args.cloud != 'envvars':
            conn = connection.Connection(cloud=args.cloud)
        else:
            conn = get_connection()
    except Exception as e:
        print(f"Error connecting to OpenStack: {e}")
        sys.exit(1)

    # Print tree view
    print_tree(
        conn,
        project_id=args.project_id,
        filter_mode=args.filter,
        collapse_mode=args.collapse,
        lb_name_or_id=args.lb,
    )


if __name__ == '__main__':
    main()

