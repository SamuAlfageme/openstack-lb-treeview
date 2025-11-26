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


def is_member_problematic(member):
    """Check if a member has issues (not ACTIVE or not ONLINE)"""
    prov_status = member.get('provisioning_status', 'UNKNOWN')
    oper_status = member.get('operating_status', 'UNKNOWN')
    return prov_status != 'ACTIVE' or oper_status != 'ONLINE'


def format_member_status(member):
    """Format member with appropriate highlighting based on status"""
    name = member.get('name', member.get('id', 'N/A'))
    prov_status = member.get('provisioning_status', 'UNKNOWN')
    oper_status = member.get('operating_status', 'UNKNOWN')

    # Build status string
    status_parts = []

    # Highlight provisioning_status if not ACTIVE
    if prov_status != 'ACTIVE':
        prov_display = f"{Colors.YELLOW}{Colors.BOLD}{prov_status}{Colors.RESET}"
        status_parts.append(f"provisioning: {prov_display}")
    else:
        status_parts.append(f"provisioning: {prov_status}")

    # Display operating_status in red if not ONLINE
    if oper_status != 'ONLINE':
        oper_display = f"{Colors.RED}{oper_status}{Colors.RESET}"
        status_parts.append(f"operating: {oper_display}")
    else:
        status_parts.append(f"operating: {oper_status}")

    status_str = " | ".join(status_parts)
    return f"{name} ({status_str})"


def print_tree(conn, project_id=None, filter_mode=False, collapse_mode=False):
    """Print tree view of loadbalancers, pools, and members

    Args:
        conn: OpenStack connection object
        project_id: Optional project ID to filter by
        filter_mode: If True, only show problematic members and pools with no members
        collapse_mode: If True, only show pool names without querying/displaying members
    """
    try:
        # Get all loadbalancers
        # Convert generator to list to allow multiple iterations if needed
        if project_id:
            loadbalancers = list(conn.load_balancer.load_balancers(project_id=project_id))
        else:
            loadbalancers = list(conn.load_balancer.load_balancers())

        if not loadbalancers:
            print("No loadbalancers found in the project.")
            return

        for lb in loadbalancers:
            # Handle both dict and object responses
            if hasattr(lb, 'name'):
                lb_name = lb.name or lb.id
                lb_id = lb.id
                lb_operating_status = getattr(lb, 'operating_status', None)
            else:
                lb_name = lb.get('name', lb.get('id', 'Unknown'))
                lb_id = lb.get('id')
                lb_operating_status = lb.get('operating_status')

            # When both filter and collapse are enabled, filter by load balancer operating_status
            if filter_mode and collapse_mode:
                # Only show load balancers with operating_status != 'ONLINE'
                if lb_operating_status == 'ONLINE':
                    continue

            # Get pools for this loadbalancer
            try:
                # Try different API patterns for getting pools
                pools = list(conn.load_balancer.pools(loadbalancer_id=lb_id))

                if collapse_mode:
                    # In collapse mode, just show pool names without members
                    pools = [(pool, None) for pool in pools]
                elif filter_mode:
                    # In filter mode, collect pools that should be shown
                    filtered_pools = []
                    for pool in pools:
                        # Handle both dict and object responses
                        if hasattr(pool, 'name'):
                            pool_id = pool.id
                        else:
                            pool_id = pool.get('id')

                        # Get members for this pool
                        try:
                            members = list(conn.load_balancer.members(pool=pool_id))

                            # Filter members to only problematic ones
                            problematic_members = []
                            for member in members:
                                # Handle both dict and object responses
                                if hasattr(member, 'name'):
                                    member_dict = {
                                        'id': member.id,
                                        'name': member.name,
                                        'provisioning_status': getattr(member, 'provisioning_status', 'UNKNOWN'),
                                        'operating_status': getattr(member, 'operating_status', 'UNKNOWN'),
                                    }
                                else:
                                    member_dict = member

                                if is_member_problematic(member_dict):
                                    problematic_members.append(member_dict)

                            # Show pool if it has no members OR has problematic members
                            if len(members) == 0 or len(problematic_members) > 0:
                                filtered_pools.append((pool, problematic_members))
                        except (OpenStackCloudException, Exception):
                            # If we can't fetch members, skip this pool in filter mode
                            pass

                    # Only show loadbalancer if it has filtered pools
                    if not filtered_pools:
                        continue

                    pools = filtered_pools
                else:
                    # In normal mode, convert pools to list of tuples (pool, None)
                    pools = [(pool, None) for pool in pools]

                if not pools:
                    if not filter_mode:
                        print(f"{Colors.BOLD}{Colors.BLUE}📦 {lb_name}{Colors.RESET} (ID: {lb_id})")
                        print(f"  └─ {Colors.BLUE}No pools{Colors.RESET}")
                        print()
                else:
                    print(f"{Colors.BOLD}{Colors.BLUE}📦 {lb_name}{Colors.RESET} (ID: {lb_id})")

                    for idx, (pool, prefiltered_members) in enumerate(pools):
                        # Handle both dict and object responses
                        if hasattr(pool, 'name'):
                            pool_name = pool.name or pool.id
                            pool_id = pool.id
                            # Convert to dict for easier access
                            pool_dict = {
                                'id': pool.id,
                                'name': pool.name,
                            }
                        else:
                            pool_name = pool.get('name', pool.get('id', 'Unknown'))
                            pool_id = pool.get('id')
                            pool_dict = pool

                        is_last_pool = (idx == len(pools) - 1)

                        # Tree connector
                        if is_last_pool:
                            prefix = "  └─"
                            member_prefix = "     "
                        else:
                            prefix = "  ├─"
                            member_prefix = "  │  "

                        print(f"{prefix} {Colors.GREEN}🏊 {pool_name}{Colors.RESET} (ID: {pool_id})")

                        # Get members for this pool (skip if collapse mode)
                        if collapse_mode:
                            # Skip member fetching and display in collapse mode
                            pass
                        else:
                            try:
                                if filter_mode:
                                    # Use pre-filtered members (already filtered to problematic ones)
                                    members = prefiltered_members

                                    # In filter mode, show empty pools or problematic members
                                    if len(members) == 0:
                                        if is_last_pool:
                                            print(f"     └─ {Colors.BLUE}No members{Colors.RESET}")
                                        else:
                                            print(f"  │  └─ {Colors.BLUE}No members{Colors.RESET}")
                                    else:
                                        # Members are already filtered to problematic ones
                                        for mem_idx, member in enumerate(members):
                                            is_last_member = (mem_idx == len(members) - 1)

                                            if is_last_pool:
                                                if is_last_member:
                                                    member_connector = "     └─"
                                                else:
                                                    member_connector = "     ├─"
                                            else:
                                                if is_last_member:
                                                    member_connector = "  │  └─"
                                                else:
                                                    member_connector = "  │  ├─"

                                            member_str = format_member_status(member)
                                            print(f"{member_connector} {Colors.BOLD}👤{Colors.RESET} {member_str}")
                                else:
                                    # Normal mode - fetch and show all members
                                    members = list(conn.load_balancer.members(pool=pool_id))
                                    # Normal mode - show all members
                                    if not members:
                                        if is_last_pool:
                                            print(f"     └─ {Colors.BLUE}No members{Colors.RESET}")
                                        else:
                                            print(f"  │  └─ {Colors.BLUE}No members{Colors.RESET}")
                                    else:
                                        for mem_idx, member in enumerate(members):
                                            # Handle both dict and object responses
                                            if hasattr(member, 'name'):
                                                member_dict = {
                                                    'id': member.id,
                                                    'name': member.name,
                                                    'provisioning_status': getattr(member, 'provisioning_status', 'UNKNOWN'),
                                                    'operating_status': getattr(member, 'operating_status', 'UNKNOWN'),
                                                }
                                            else:
                                                member_dict = member

                                            is_last_member = (mem_idx == len(members) - 1)

                                            if is_last_pool:
                                                if is_last_member:
                                                    member_connector = "     └─"
                                                else:
                                                    member_connector = "     ├─"
                                            else:
                                                if is_last_member:
                                                    member_connector = "  │  └─"
                                                else:
                                                    member_connector = "  │  ├─"

                                            member_str = format_member_status(member_dict)
                                            print(f"{member_connector} {Colors.BOLD}👤{Colors.RESET} {member_str}")

                            except (OpenStackCloudException, Exception) as e:
                                print(f"{member_prefix}└─ {Colors.RED}Error fetching members: {e}{Colors.RESET}")

            except (OpenStackCloudException, Exception) as e:
                if not filter_mode:
                    print(f"{Colors.BOLD}{Colors.BLUE}📦 {lb_name}{Colors.RESET} (ID: {lb_id})")
                    print(f"  └─ {Colors.RED}Error fetching pools: {e}{Colors.RESET}")
                    print()

            if not filter_mode or (filter_mode and pools):
                print()  # Empty line between loadbalancers

    except (OpenStackCloudException, Exception) as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Display a tree view of OpenStack loadbalancers, pools, and members'
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
        help='Collapse mode: only show pool names without querying or displaying members (faster)'
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
    print_tree(conn, project_id=args.project_id, filter_mode=args.filter, collapse_mode=args.collapse)


if __name__ == '__main__':
    main()

