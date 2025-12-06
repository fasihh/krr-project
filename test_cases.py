"""
Test ReBAC (Relationship-Based Access Control) with Fuseki
Based on OpenFGA Guild/Role authorization model
Ported from TypeScript test suite
"""

from typing import Dict, Optional, Callable
from dataclasses import dataclass

from main import (
    clear_all_data,
    create_user,
    create_guild,
    add_member,
    create_role,
    assign_role,
    remove_role,
    change_owner,
    check_permission
)
import database as db


@dataclass
class TestCase:
    id: int
    actor_key: str
    relation: str
    expected: bool
    description: str
    prepare: Optional[Callable[[Dict[str, str]], None]] = None


# Define all test cases from the TypeScript suite
test_cases = [
    TestCase(
        id=1,
        actor_key='A',
        relation='can_change_owner',
        expected=True,
        description='Owner can change owner'
    ),
    TestCase(
        id=2,
        actor_key='A',
        relation='can_ban_members',
        expected=True,
        description='Owner inherits moderator permissions'
    ),
    TestCase(
        id=3,
        actor_key='B',
        relation='can_message',
        expected=True,
        description='Member can message',
        prepare=lambda guildIds: add_member(guildIds['A'], 'B')
    ),
    TestCase(
        id=4,
        actor_key='B',
        relation='can_add_members',
        expected=False,
        description='Member cannot add members'
    ),
    TestCase(
        id=5,
        actor_key='C',
        relation='can_add_members',
        expected=True,
        description='Moderator can add members',
        prepare=lambda guildIds: (
            add_member(guildIds['A'], 'C'),
            create_role(guildIds['A'], 'Admin', ['moderator']),
            assign_role(guildIds['A'], 'C', 'Admin'),
            add_member(guildIds['A'], 'D')
        )
    ),
    TestCase(
        id=6,
        actor_key='C',
        relation='can_manage_roles',
        expected=True,
        description='Moderator can manage roles',
        prepare=lambda guildIds: assign_role(guildIds['A'], 'D', 'Admin')
    ),
    TestCase(
        id=7,
        actor_key='C',
        relation='can_change_owner',
        expected=False,
        description='Moderator cannot change owner'
    ),
    TestCase(
        id=8,
        actor_key='D',
        relation='can_manage_permissions',
        expected=True,
        description='Role grants can_manage_permissions',
        prepare=lambda guildIds: (
            add_member(guildIds['A'], 'E'),
            create_role(guildIds['A'], 'Kabil', ['can_manage_permissions']),
            assign_role(guildIds['A'], 'D', 'Kabil')
        )
    ),
    TestCase(
        id=9,
        actor_key='D',
        relation='can_ban_members',
        expected=True,
        description='Role grants can_ban_members via inheritance'
    ),
    TestCase(
        id=10,
        actor_key='E',
        relation='can_add_members',
        expected=False,
        description='Role with no permissions grants nothing',
        prepare=lambda guildIds: (
            create_role(guildIds['A'], 'Helper', ['can_message']),
            assign_role(guildIds['A'], 'E', 'Helper'),
            add_member(guildIds['A'], 'F')
        )
    ),
    TestCase(
        id=11,
        actor_key='F',
        relation='can_add_members',
        expected=True,
        description='Member + Role grants permission',
        prepare=lambda guildIds: (
            create_role(guildIds['A'], 'EventManager', ['can_add_members']),
            assign_role(guildIds['A'], 'F', 'EventManager')
        )
    ),
    TestCase(
        id=12,
        actor_key='F',
        relation='can_ban_members',
        expected=False,
        description='Member + Role does not grant ban permissions'
    ),
    TestCase(
        id=13,
        actor_key='G',
        relation='can_manage_roles',
        expected=True,
        description='Moderator + Role grants permission (OR logic)',
        prepare=lambda guildIds: (
            add_member(guildIds['A'], 'G'),
            create_role(guildIds['A'], 'SpecialRole', ['can_manage_roles']),
            assign_role(guildIds['A'], 'G', 'SpecialRole'),
            assign_role(guildIds['A'], 'G', 'Admin')
        )
    ),
    TestCase(
        id=14,
        actor_key='H',
        relation='can_manage_channels',
        expected=True,
        description='Owner + Role: owner privileges override role',
        prepare=lambda guildIds: (
            add_member(guildIds['A'], 'H'),
            change_owner(guildIds['A'], 'H')
        )
    ),
    TestCase(
        id=15,
        actor_key='I',
        relation='can_manage_permissions',
        expected=False,
        description='Member cannot manage permissions',
        prepare=lambda guildIds: add_member(guildIds['A'], 'I')
    ),
    TestCase(
        id=16,
        actor_key='J',
        relation='can_ban_members',
        expected=True,
        description='Moderator can ban via inheritance chain',
        prepare=lambda guildIds: (
            change_owner(guildIds['A'], 'A'),
            add_member(guildIds['A'], 'J'),
            assign_role(guildIds['A'], 'J', 'Admin')
        )
    ),
    TestCase(
        id=17,
        actor_key='K',
        relation='can_ban_members',
        expected=True,
        description='Multiple roles cumulative permission',
        prepare=lambda guildIds: (
            add_member(guildIds['A'], 'K'),
            create_role(guildIds['A'], 'RoleA', ['can_manage_roles']),
            create_role(guildIds['A'], 'RoleB', ['can_manage_permissions']),
            assign_role(guildIds['A'], 'K', 'RoleA'),
            assign_role(guildIds['A'], 'K', 'RoleB')
        )
    ),
    TestCase(
        id=18,
        actor_key='L',
        relation='can_message',
        expected=True,
        description='User with member role can message',
        prepare=lambda guildIds: add_member(guildIds['A'], 'L')
    ),
    TestCase(
        id=19,
        actor_key='M',
        relation='can_message',
        expected=False,
        description='Moderator in different guild cannot message',
        prepare=lambda guildIds: (
            add_member(guildIds['H'], 'M'),
            create_role(guildIds['H'], 'Admin', ['moderator']),
            assign_role(guildIds['H'], 'M', 'Admin')
        )
    ),
    TestCase(
        id=20,
        actor_key='N',
        relation='can_manage_roles',
        expected=False,
        description='Member cannot manage roles',
        prepare=lambda guildIds: add_member(guildIds['A'], 'N')
    ),
    TestCase(
        id=21,
        actor_key='O',
        relation='can_add_members',
        expected=False,
        description='Role in wrong guild does not grant permissions',
        prepare=lambda guildIds: (
            add_member(guildIds['H'], 'O'),
            assign_role(guildIds['H'], 'O', 'Admin')
        )
    ),
    TestCase(
        id=26,
        actor_key='S',
        relation='can_add_members',
        expected=False,
        description='Moderator demoted to member loses permission',
        prepare=lambda guildIds: (
            add_member(guildIds['A'], 'S'),
            assign_role(guildIds['A'], 'S', 'Admin'),
            remove_role(guildIds['A'], 'S', 'Admin')
        )
    ),
]


def main():
    print("=" * 70)
    print("ReBAC Testing with Apache Jena Fuseki")
    print("OpenFGA-style Guild/Role Authorization Model")
    print("Ported from TypeScript test suite")
    print("=" * 70)
    
    # Clear existing data
    clear_all_data()
    
    # Create users
    print("\nCreating users...")
    user_keys = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'S']
    for key in user_keys:
        create_user(key, f"User {key}")
    print(f"Created {len(user_keys)} users")
    
    # Create guilds
    print("\nCreating guilds...")
    create_guild('A', 'Test Guild 1', 'A')
    create_guild('H', 'Test Guild 2', 'H')
    print("Created 2 guilds")
    
    # Get guild IDs from database
    guild_a = db.get_guild('A')
    guild_h = db.get_guild('H')
    guild_ids = {
        'A': guild_a['guild_id'],
        'H': guild_h['guild_id']
    }
    
    # Run test cases
    print("\n" + "=" * 70)
    print("Running test cases...")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for tc in test_cases:
        print(f"\nTC{tc.id}: {tc.description}")
        print(f"  Actor: {tc.actor_key}, Relation: {tc.relation}, Expected: {tc.expected}")
        
        # Run prepare if exists
        if tc.prepare:
            try:
                result = tc.prepare(guild_ids)
                # Handle tuple returns from lambda
                if result is not None:
                    pass
            except Exception as e:
                print(f"  ✗ Prepare failed: {e}")
                failed += 1
                continue
        
        # Check permission
        allowed = check_permission(tc.actor_key, guild_ids['A'], tc.relation)
        
        # Compare result
        if allowed == tc.expected:
            print(f"  ✓ PASSED: allowed={allowed}")
            passed += 1
        else:
            print(f"  ✗ FAILED: expected={tc.expected}, got={allowed}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed out of {len(test_cases)} total")
    print("=" * 70)
    
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)