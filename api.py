from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware

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

guildPermissions = [
  'can_add_members',
  'can_ban_members',
  'can_change_owner',
  'can_kick_members',
  'can_manage_channels',
  'can_manage_permissions',
  'can_manage_roles',
  'can_message'
]

app = FastAPI(title="ReBAC Guild/Role API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserRequest(BaseModel):
    key: str
    name: str

class GuildRequest(BaseModel):
    key: str
    name: str
    owner_key: str

class MemberRequest(BaseModel):
    guild_id: str
    user_key: str

class RoleRequest(BaseModel):
    guild_id: str
    role_name: str
    permissions: List[str]

class AssignRoleRequest(BaseModel):
    guild_id: str
    user_key: str
    role_name: str

class RemoveRoleRequest(BaseModel):
    guild_id: str
    user_key: str
    role_name: str

class OwnerChangeRequest(BaseModel):
    guild_id: str
    new_owner_key: str

class PermissionCheckRequest(BaseModel):
    user_key: str
    guild_id: str
    relation: str


@app.get("/")
def root():
    stats = db.get_db_stats()
    return {
        "message": "ReBAC Guild/Role API",
        "database": stats
    }


@app.post("/reset")
def reset_database():
    clear_all_data()
    return {"status": "database_cleared"}


@app.get("/users")
def list_users():
    users = db.get_all_users()
    return {"users": users}


@app.get("/guilds")
def list_guilds():
    guilds = db.get_all_guilds()
    return {"guilds": guilds}


@app.post("/user/create")
def api_create_user(req: UserRequest):
    success = create_user(req.key, req.name)
    if not success:
        raise HTTPException(status_code=400, detail="User already exists or creation failed")
    
    user = db.get_user(req.key)
    return {"status": "user_created", "user": user}


@app.post("/guild/create")
def api_create_guild(req: GuildRequest):
    success = create_guild(req.key, req.name, req.owner_key)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to create guild")
    
    guild = db.get_guild(req.key)
    return {"status": "guild_created", "guild": guild}


@app.post("/guild/add_member")
def api_add_member(req: MemberRequest):
    success = add_member(req.guild_id, req.user_key)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add member")
    return {"status": "member_added"}


@app.post("/role/create")
def api_create_role(req: RoleRequest):
    for p in req.permissions:
        if p not in guildPermissions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid permission: {p}"
            )

    role_id = create_role(req.guild_id, req.role_name, req.permissions)
    return {"status": "role_created", "role_id": role_id}


@app.post("/role/assign")
def api_assign_role(req: AssignRoleRequest):
    success = assign_role(req.guild_id, req.user_key, req.role_name)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to assign role")
    return {"status": "role_assigned"}


@app.post("/role/remove")
def api_remove_role(req: RemoveRoleRequest):
    success = remove_role(req.guild_id, req.user_key, req.role_name)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove role")
    return {"status": "role_removed"}


@app.post("/guild/change_owner")
def api_change_owner(req: OwnerChangeRequest):
    success = change_owner(req.guild_id, req.new_owner_key)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to change owner")
    return {"status": "owner_changed"}


@app.post("/permission/check")
def api_check_permission(req: PermissionCheckRequest):
    allowed = check_permission(req.user_key, req.guild_id, req.relation)
    return {
        "user": req.user_key,
        "relation": req.relation,
        "allowed": allowed
    }
