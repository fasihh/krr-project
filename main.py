"""
ReBAC (Relationship-Based Access Control) with Fuseki
Based on OpenFGA Guild/Role authorization model
Core functions for user, guild, role, and permission management
Now with SQLite for persistent storage
"""

import requests
from typing import Optional
from dataclasses import dataclass

import database as db

FUSEKI_BASE = "http://localhost:3030/rebac"
QUERY_ENDPOINT = f"{FUSEKI_BASE}/query"
UPDATE_ENDPOINT = f"{FUSEKI_BASE}/update"

# Initialize database on import
db.init_db()

@dataclass
class User:
    user_id: str
    name: str
    
@dataclass
class Guild:
    guild_id: str
    name: str
    owner_id: str

def execute_update(sparql_update: str, silent: bool = False) -> bool:
    """Execute a SPARQL UPDATE query"""
    response = requests.post(
        UPDATE_ENDPOINT,
        data={'update': sparql_update},
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    if response.status_code == 200:
        if not silent:
            print(f"Update successful")
    else:
        print(f"Update failed: {response.status_code}")
        print(response.text)
    return response.status_code == 200

def execute_query(sparql_query: str) -> Optional[dict]:
    """Execute a SPARQL SELECT query"""
    response = requests.post(
        QUERY_ENDPOINT,
        data={'query': sparql_query},
        headers={'Accept': 'application/sparql-results+json'}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Query failed: {response.status_code}")
        return None

def clear_all_data():
    """Clear all data from both Fuseki and SQLite"""
    print("Clearing all data...")
    # Clear Fuseki
    update = "DELETE WHERE { ?s ?p ?o }"
    execute_update(update, silent=True)
    # Clear SQLite
    db.clear_all_data()

def create_user(user_id: str) -> bool:
    """Create a user in both SQLite and Fuseki"""
    
    if not db.save_user(user_id):
        print(f"User {user_id} already exists in database")
        return False
    
    # Save to Fuseki
    update = f"""
    PREFIX rebac: <http://example.org/rebac#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    INSERT DATA {{
        rebac:user_{user_id} rdf:type rebac:User ;
    }}
    """
    return execute_update(update, silent=True)

def create_guild(guild_id: str, owner_id: str) -> bool:
    """Create a guild with an owner in both SQLite and Fuseki"""
    
    # Get owner from database
    user_data = db.get_user(owner_id)
    if not user_data:
        print(f"Owner {owner_id} not found")
        return False
    
    owner_id = user_data['user_id']
    
    if not db.save_guild(guild_id, owner_id):
        print(f"Guild {guild_id} already exists in database")
        return False
    
    # Save to Fuseki
    update = f"""
    PREFIX rebac: <http://example.org/rebac#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    INSERT DATA {{
        rebac:guild_{guild_id} rdf:type rebac:Guild ;
            rebac:owner rebac:user_{owner_id} .
    }}
    """
    return execute_update(update, silent=True)

def delete_guild(guild_id: str) -> bool:
    """Delete a guild from both SQLite and Fuseki"""
    
    # Delete all roles for this guild first
    db.delete_guild_roles(guild_id)
    
    # Delete the guild
    if not db.delete_guild(guild_id):
        print(f"Guild {guild_id} not found in database")
        return False
    
    # Delete all related triples in Fuseki (same as above)
    update = f"""
    PREFIX rebac: <http://example.org/rebac#>
    
    DELETE {{
        rebac:guild_{guild_id} ?p ?o .
        ?s ?p2 rebac:guild_{guild_id} .
        ?role ?rp ?ro .
    }}
    WHERE {{
        {{
            rebac:guild_{guild_id} ?p ?o .
        }}
        UNION
        {{
            ?s ?p2 rebac:guild_{guild_id} .
        }}
        UNION
        {{
            ?role rebac:parent rebac:guild_{guild_id} .
            ?role ?rp ?ro .
        }}
    }}
    """
    return execute_update(update, silent=True)

def add_member(guild_id: str, member_id: str, role_id: str) -> bool:
    """Add a member to a guild"""
    user_data = db.get_user(member_id)
    if not user_data:
        print(f"User {member_id} not found")
        return False
    
    update = f"""
    PREFIX rebac: <http://example.org/rebac#>
    
    INSERT DATA {{
        rebac:guild_{guild_id} rebac:member rebac:user_{member_id} .
    }}
    """
    execute_update(update, silent=True)

    return assign_role(guild_id, member_id, role_id)
    

def remove_member_from_guild(guild_id: str, member_id: str, role_ids: list[str]) -> bool:
    """Remove a member from a guild"""
    user_data = db.get_user(member_id)
    if not user_data:
        print(f"User {member_id} not found")
        return False

    update = f"""
    PREFIX rebac: <http://example.org/rebac#>
    
    DELETE {{
        rebac:guild_{guild_id} rebac:member rebac:user_{member_id} .
        rebac:guild_{guild_id} rebac:moderator rebac:user_{member_id} .
    }}
    WHERE {{
        rebac:guild_{guild_id} rebac:member rebac:user_{member_id} .
        OPTIONAL {{ rebac:guild_{guild_id} rebac:moderator rebac:user_{member_id} . }}
    }}
    """
    
    for role_id in role_ids:
        remove_role_from_member(guild_id, member_id, role_id)

    return execute_update(update, silent=True)

def create_role(guild_id: str, role_id: str, permissions: list[str]) -> str:
    """Create a role in a guild with specified permissions"""
    
    db.save_role(role_id, guild_id)
    
    grant_statements = []
    
    # Check if moderator permission is included
    is_moderator = 'moderator' in permissions
    
    if is_moderator:
        grant_statements.append(f"rebac:role_{role_id} rebac:grants_moderator true .")
    
    if 'can_manage_permissions' in permissions or is_moderator:
        grant_statements.append(f"rebac:role_{role_id} rebac:grants_manage_permissions true .")
    if 'can_manage_channels' in permissions or is_moderator:
        grant_statements.append(f"rebac:role_{role_id} rebac:grants_manage_channels true .")
    if 'can_kick_members' in permissions or is_moderator:
        grant_statements.append(f"rebac:role_{role_id} rebac:grants_kick_members true .")
    if 'can_ban_members' in permissions or is_moderator:
        grant_statements.append(f"rebac:role_{role_id} rebac:grants_ban_members true .")
    if 'can_add_members' in permissions or is_moderator:
        grant_statements.append(f"rebac:role_{role_id} rebac:grants_add_members true .")
    if 'can_message' in permissions or is_moderator:
        grant_statements.append(f"rebac:role_{role_id} rebac:grants_message true .")
    if 'can_manage_roles' in permissions or is_moderator:
        grant_statements.append(f"rebac:role_{role_id} rebac:grants_manage_roles true .")
    
    grants = "\n        ".join(grant_statements) if grant_statements else ""
    
    update = f"""
    PREFIX rebac: <http://example.org/rebac#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    INSERT DATA {{
        rebac:role_{role_id} rdf:type rebac:Role ;
            rebac:parent rebac:guild_{guild_id} .
        {grants}
        rebac:guild_{guild_id} rebac:has_role rebac:role_{role_id} .
    }}
    """
    execute_update(update, silent=True)
    return role_id

def assign_role(guild_id: str, member_id: str, role_id: str) -> bool:
    """Assign a role to a member"""
    user_data = db.get_user(member_id)
    if not user_data:
        print(f"User {member_id} not found")
        return False
    
    # Check if this role grants moderator permission by querying Fuseki
    check_moderator = f"""
    PREFIX rebac: <http://example.org/rebac#>
    ASK {{
        rebac:role_{role_id} rebac:grants_moderator true .
    }}
    """
    result = execute_query(check_moderator)
    is_moderator_role = result.get('boolean', False) if result else False
    
    if is_moderator_role:
        update = f"""
        PREFIX rebac: <http://example.org/rebac#>
        
        INSERT DATA {{
            rebac:role_{role_id} rebac:has_role rebac:user_{member_id} .
            rebac:guild_{guild_id} rebac:moderator rebac:user_{member_id} .
        }}
        """
    else:
        update = f"""
        PREFIX rebac: <http://example.org/rebac#>
        
        INSERT DATA {{
            rebac:role_{role_id} rebac:has_role rebac:user_{member_id} .
        }}
        """
    return execute_update(update, silent=True)

def delete_role(role_id: str, guild_id: str) -> bool:
    """Delete a role from both SQLite and Fuseki"""
    db.delete_role(role_id)
    
    update = f"""
    PREFIX rebac: <http://example.org/rebac#>
    
    DELETE WHERE {{
        rebac:role_{role_id} ?p ?o .
        rebac:guild_{guild_id} rebac:has_role rebac:role_{role_id} .
    }}
    """
    return execute_update(update, silent=True)

def remove_role_from_member(guild_id: str, member_id: str, role_id: str) -> bool:
    """Remove a role from a member"""
    user_data = db.get_user(member_id)
    if not user_data:
        print(f"User {member_id} not found")
        return False
    
    check_moderator = f"""
    PREFIX rebac: <http://example.org/rebac#>
    ASK {{
        rebac:role_{role_id} rebac:grants_moderator true .
    }}
    """
    result = execute_query(check_moderator)
    is_moderator_role = result.get('boolean', False) if result else False

    if is_moderator_role:
        update = f"""
        PREFIX rebac: <http://example.org/rebac#>
        
        DELETE {{
            rebac:role_{role_id} rebac:has_role rebac:user_{member_id} .
            rebac:guild_{guild_id} rebac:moderator rebac:user_{member_id} .
        }}
        WHERE {{
            rebac:role_{role_id} rebac:has_role rebac:user_{member_id} .
            OPTIONAL {{ rebac:guild_{guild_id} rebac:moderator rebac:user_{member_id} . }}
        }}
        """
    else:
        update = f"""
        PREFIX rebac: <http://example.org/rebac#>
        
        DELETE {{
            rebac:role_{role_id} rebac:has_role rebac:user_{member_id} .
        }}
        WHERE {{
            rebac:role_{role_id} rebac:has_role rebac:user_{member_id} .
        }}
        """
    return execute_update(update, silent=True)

def change_owner(guild_id: str, new_owner_id: str) -> bool:
    """Change guild ownership"""
    user_data = db.get_user(new_owner_id)
    if not user_data:
        print(f"User {new_owner_id} not found")
        return False
    
    db.update_guild_owner(guild_id, new_owner_id)
    
    # Update in Fuseki
    update = f"""
    PREFIX rebac: <http://example.org/rebac#>
    
    DELETE {{
        rebac:guild_{guild_id} rebac:owner ?old_owner .
    }}
    INSERT {{
        rebac:guild_{guild_id} rebac:owner rebac:user_{new_owner_id} .
    }}
    WHERE {{
        rebac:guild_{guild_id} rebac:owner ?old_owner .
    }}
    """
    return execute_update(update, silent=True)

def check_permission(user_id: str, guild_id: str, relation: str) -> bool:
    """Check if a user has a specific permission on a guild"""
    user_data = db.get_user(user_id)
    if not user_data:
        print(f"User {user_id} not found")
        return False
    
    query = f"""
    PREFIX rebac: <http://example.org/rebac#>
    
    ASK {{
        rebac:guild_{guild_id} rebac:{relation} rebac:user_{user_id} .
    }}
    """
    
    result = execute_query(query)
    if result:
        return result.get('boolean', False)
    return False

def check_role_permission(role_id: str, relation: str, guild_id: str) -> bool:
    """Check if a role grants a specific permission"""
    query = f"""
    PREFIX rebac: <http://example.org/rebac#>
    
    ASK {{
        rebac:role_{role_id} rebac:parent rebac:guild_{guild_id} ;
                            rebac:grants_{relation} true .
    }}
    """
    
    result = execute_query(query)
    if result:
        return result.get('boolean', False)
    return False