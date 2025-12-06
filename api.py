from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware

from main import (
    TestContext,
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


ctx = TestContext()

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


@app.post("/reset")
def reset_database():
    clear_all_data()
    ctx.users.clear()
    ctx.guilds.clear()
    return {"status": "database_cleared"}


@app.post("/user/create")
def api_create_user(req: UserRequest):
    create_user(ctx, req.key, req.name)
    return {"status": "user_created", "user": ctx.users[req.key].__dict__}


@app.post("/guild/create")
def api_create_guild(req: GuildRequest):
    create_guild(ctx, req.key, req.name, req.owner_key)
    return {"status": "guild_created", "guild": ctx.guilds[req.key].__dict__}


@app.post("/guild/add_member")
def api_add_member(req: MemberRequest):
    add_member(ctx, req.guild_id, req.user_key)
    return {"status": "member_added"}


@app.post("/role/create")
def api_create_role(req: RoleRequest):
    for p in req.permissions:
        if p not in guildPermissions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid permission: {p}"
            )

    role_id = create_role(ctx, req.guild_id, req.role_name, req.permissions)
    return {"status": "role_created", "role_id": role_id}


@app.post("/role/assign")
def api_assign_role(req: AssignRoleRequest):
    assign_role(ctx, req.guild_id, req.user_key, req.role_name)
    return {"status": "role_assigned"}


@app.post("/role/remove")
def api_remove_role(req: RemoveRoleRequest):
    remove_role(ctx, req.guild_id, req.user_key, req.role_name)
    return {"status": "role_removed"}


@app.post("/guild/change_owner")
def api_change_owner(req: OwnerChangeRequest):
    change_owner(ctx, req.guild_id, req.new_owner_key)
    return {"status": "owner_changed"}


@app.post("/permission/check")
def api_check_permission(req: PermissionCheckRequest):
    allowed = check_permission(ctx, req.user_key, req.guild_id, req.relation)
    return {
        "user": req.user_key,
        "relation": req.relation,
        "allowed": allowed
    }
