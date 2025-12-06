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

def create_user(user_key: str, name: str) -> bool:
    """Create a user in both SQLite and Fuseki"""
    user_id = f"user_{user_key}"
    
    if not db.save_user(user_key, user_id, name):
        print(f"User {user_key} already exists in database")
        return False
    
    # Save to Fuseki
    update = f"""
    PREFIX rebac: <http://example.org/rebac#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    INSERT DATA {{
        rebac:{user_id} rdf:type rebac:User ;
            rebac:name "{name}" .
    }}
    """
    return execute_update(update, silent=True)

def create_guild(guild_key: str, name: str, owner_key: str) -> bool:
    """Create a guild with an owner in both SQLite and Fuseki"""
    guild_id = f"guild_{guild_key}"
    
    # Get owner from database
    user_data = db.get_user(owner_key)
    if not user_data:
        print(f"Owner {owner_key} not found")
        return False
    
    owner_id = user_data['user_id']
    
    if not db.save_guild(guild_key, guild_id, name, owner_id):
        print(f"Guild {guild_key} already exists in database")
        return False
    
    # Save to Fuseki
    update = f"""
    PREFIX rebac: <http://example.org/rebac#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    INSERT DATA {{
        rebac:{guild_id} rdf:type rebac:Guild ;
            rebac:name "{name}" ;
            rebac:owner rebac:{owner_id} .
    }}
    """
    return execute_update(update, silent=True)

def add_member(guild_id: str, member_key: str) -> bool:
    """Add a member to a guild"""
    user_data = db.get_user(member_key)
    if not user_data:
        print(f"User {member_key} not found")
        return False
    
    member_id = user_data['user_id']
    
    update = f"""
    PREFIX rebac: <http://example.org/rebac#>
    
    INSERT DATA {{
        rebac:{guild_id} rebac:member rebac:{member_id} .
    }}
    """
    return execute_update(update, silent=True)

def create_role(guild_id: str, role_name: str, permissions: list[str]) -> str:
    """Create a role in a guild with specified permissions"""
    role_id = f"role_{role_name.replace(' ', '_')}"
    
    db.save_role(role_id, role_name, guild_id)
    
    grant_statements = []
    if 'moderator' in permissions:
        pass
    if 'can_manage_permissions' in permissions:
        grant_statements.append(f"rebac:{role_id} rebac:grants_manage_permissions true .")
    if 'can_manage_channels' in permissions:
        grant_statements.append(f"rebac:{role_id} rebac:grants_manage_channels true .")
    if 'can_kick_members' in permissions:
        grant_statements.append(f"rebac:{role_id} rebac:grants_kick_members true .")
    if 'can_ban_members' in permissions:
        grant_statements.append(f"rebac:{role_id} rebac:grants_ban_members true .")
    if 'can_add_members' in permissions:
        grant_statements.append(f"rebac:{role_id} rebac:grants_add_members true .")
    if 'can_message' in permissions:
        grant_statements.append(f"rebac:{role_id} rebac:grants_message true .")
    if 'can_manage_roles' in permissions:
        grant_statements.append(f"rebac:{role_id} rebac:grants_manage_roles true .")
    
    grants = "\n        ".join(grant_statements) if grant_statements else ""
    
    update = f"""
    PREFIX rebac: <http://example.org/rebac#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    INSERT DATA {{
        rebac:{role_id} rdf:type rebac:Role ;
            rebac:name "{role_name}" ;
            rebac:parent rebac:{guild_id} .
        {grants}
        rebac:{guild_id} rebac:has_role rebac:{role_id} .
    }}
    """
    execute_update(update, silent=True)
    return role_id

def assign_role(guild_id: str, member_key: str, role_name: str) -> bool:
    """Assign a role to a member"""
    user_data = db.get_user(member_key)
    if not user_data:
        print(f"User {member_key} not found")
        return False
    
    member_id = user_data['user_id']
    role_id = f"role_{role_name.replace(' ', '_')}"
    
    is_moderator_role = role_name == 'Admin' 
    if is_moderator_role:
        update = f"""
        PREFIX rebac: <http://example.org/rebac#>
        
        INSERT DATA {{
            rebac:{role_id} rebac:has_role rebac:{member_id} .
            rebac:{guild_id} rebac:moderator rebac:{member_id} .
        }}
        """
    else:
        update = f"""
        PREFIX rebac: <http://example.org/rebac#>
        
        INSERT DATA {{
            rebac:{role_id} rebac:has_role rebac:{member_id} .
        }}
        """
    return execute_update(update, silent=True)

def remove_role(guild_id: str, member_key: str, role_name: str) -> bool:
    """Remove a role from a member"""
    user_data = db.get_user(member_key)
    if not user_data:
        print(f"User {member_key} not found")
        return False
    
    member_id = user_data['user_id']
    role_id = f"role_{role_name.replace(' ', '_')}"
    
    is_moderator_role = role_name == 'Admin'
    if is_moderator_role:
        update = f"""
        PREFIX rebac: <http://example.org/rebac#>
        
        DELETE {{
            rebac:{role_id} rebac:has_role rebac:{member_id} .
            rebac:{guild_id} rebac:moderator rebac:{member_id} .
        }}
        WHERE {{
            rebac:{role_id} rebac:has_role rebac:{member_id} .
            OPTIONAL {{ rebac:{guild_id} rebac:moderator rebac:{member_id} . }}
        }}
        """
    else:
        update = f"""
        PREFIX rebac: <http://example.org/rebac#>
        
        DELETE {{
            rebac:{role_id} rebac:has_role rebac:{member_id} .
        }}
        WHERE {{
            rebac:{role_id} rebac:has_role rebac:{member_id} .
        }}
        """
    return execute_update(update, silent=True)

def change_owner(guild_id: str, new_owner_key: str) -> bool:
    """Change guild ownership"""
    user_data = db.get_user(new_owner_key)
    if not user_data:
        print(f"User {new_owner_key} not found")
        return False
    
    new_owner_id = user_data['user_id']
    
    db.update_guild_owner(guild_id, new_owner_id)
    
    # Update in Fuseki
    update = f"""
    PREFIX rebac: <http://example.org/rebac#>
    
    DELETE {{
        rebac:{guild_id} rebac:owner ?old_owner .
    }}
    INSERT {{
        rebac:{guild_id} rebac:owner rebac:{new_owner_id} .
    }}
    WHERE {{
        rebac:{guild_id} rebac:owner ?old_owner .
    }}
    """
    return execute_update(update, silent=True)

def check_permission(user_key: str, guild_id: str, relation: str) -> bool:
    """Check if a user has a specific permission on a guild"""
    user_data = db.get_user(user_key)
    if not user_data:
        print(f"User {user_key} not found")
        return False
    
    user_id = user_data['user_id']
    
    query = f"""
    PREFIX rebac: <http://example.org/rebac#>
    
    ASK {{
        rebac:{guild_id} rebac:{relation} rebac:{user_id} .
    }}
    """
    
    result = execute_query(query)
    if result:
        return result.get('boolean', False)
    return False
