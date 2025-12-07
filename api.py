from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import List
from fastapi.middleware.cors import CORSMiddleware

from main import (
    check_role_permission,
    clear_all_data,
    create_user,
    create_guild,
    add_member,
    create_role,
    assign_role,
    delete_guild,
    delete_role,
    remove_member_from_guild,
    change_owner,
    check_permission,
    remove_role_from_member
)
import database as db

guildPermissions = [
  'moderator',
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
    user_id: str
class GuildRequest(BaseModel):
    guild_id: str
    owner_id: str

class MemberRequest(BaseModel):
    guild_id: str
    user_id: str
    role_id: str

class RoleRequest(BaseModel):
    guild_id: str
    role_id: str
    permissions: List[str]

class AssignRoleRequest(BaseModel):
    guild_id: str
    user_id: str
    role_id: str

class RemoveRoleRequest(BaseModel):
    guild_id: str
    user_id: str
    role_id: str
class OwnerChangeRequest(BaseModel):
    guild_id: str
    new_owner_id: str

class PermissionCheckRequest(BaseModel):
    user_id: str
    guild_id: str
    relation: str

class RemoveUserFromGuildRequest(BaseModel):
    guild_id: str
    user_id: str
    role_ids: List[str]

class RolePermissionCheckRequest(BaseModel):
    role_id: str
    guild_id: str
    relation: str

class DeleteRoleRequest(BaseModel):
    role_id: str
    guild_id: str

class DeleteGuildRequest(BaseModel):
    guild_id: str


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

@app.get("/roles/{guild_id}")
def list_roles(guild_id: str):
    roles = db.get_guild_roles(guild_id)
    return {"roles": roles}


@app.post("/user/create")
def api_create_user(req: UserRequest):
    success = create_user(req.user_id)
    if not success:
        raise HTTPException(status_code=400, detail="User already exists or creation failed")
    
    user = db.get_user(req.user_id)
    return {"status": "user_created", "user": user}


@app.post("/guild/create")
def api_create_guild(req: GuildRequest):
    success = create_guild(req.guild_id, req.owner_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to create guild")
    
    guild = db.get_guild(req.guild_id)
    return {"status": "guild_created", "guild": guild}

@app.post("/guild/delete")
def api_delete_guild(req: DeleteGuildRequest):
    success = delete_guild(req.guild_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete guild")
    return {"status": "guild_deleted"}

@app.post("/guild/add_member")
def api_add_member(req: MemberRequest):
    success = add_member(req.guild_id, req.user_id, req.role_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add member")
    return {"status": "member_added"}

@app.post("/guild/remove_user")
def api_remove_user_from_guild(req: RemoveUserFromGuildRequest):
    success = remove_member_from_guild(req.guild_id, req.user_id, req.role_ids)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove user from guild")
    return {"status": "user_removed_from_guild"}


@app.post("/role/create")
def api_create_role(req: RoleRequest):
    for p in req.permissions:
        if p not in guildPermissions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid permission: {p}"
            )

    role_id = create_role(req.guild_id, req.role_id, req.permissions)
    return {"status": "role_created", "role_id": role_id}


@app.post("/role/assign")
def api_assign_role(req: AssignRoleRequest):
    success = assign_role(req.guild_id, req.user_id, req.role_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to assign role")
    return {"status": "role_assigned"}


@app.post("/role/remove")
def api_remove_role(req: RemoveRoleRequest):
    success = remove_role_from_member(req.guild_id, req.user_id, req.role_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove role")
    return {"status": "role_removed"}

@app.post("/role/delete")
def api_delete_role(req: DeleteRoleRequest):
    success = delete_role(req.role_id, req.guild_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete role")
    return {"status": "role_deleted"}

@app.post("/guild/change_owner")
def api_change_owner(req: OwnerChangeRequest):
    success = change_owner(req.guild_id, req.new_owner_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to change owner")
    return {"status": "owner_changed"}


@app.post("/permission/check")
def api_check_permission(req: PermissionCheckRequest):
    allowed = check_permission(req.user_id, req.guild_id, req.relation)
    return {
        "user": req.user_id,
        "relation": req.relation,
        "allowed": allowed
    }

@app.post("/role/permission_check")
def api_check_role_permission(req: RolePermissionCheckRequest):
    allowed = check_role_permission(req.role_id, req.relation, req.guild_id)
    return {
        "role": req.role_id,
        "relation": req.relation,
        "allowed": allowed
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8569)
