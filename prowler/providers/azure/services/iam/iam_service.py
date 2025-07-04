from dataclasses import dataclass
from typing import List

from azure.mgmt.authorization import AuthorizationManagementClient

from prowler.lib.logger import logger
from prowler.providers.azure.azure_provider import AzureProvider
from prowler.providers.azure.lib.service.service import AzureService


class IAM(AzureService):
    def __init__(self, provider: AzureProvider):
        super().__init__(AuthorizationManagementClient, provider)
        self.roles, self.custom_roles = self._get_roles()
        self.role_assignments = self._get_role_assignments()

    def _get_roles(self):
        logger.info("IAM - Getting roles...")
        builtin_roles = {}
        custom_roles = {}
        for subscription, client in self.clients.items():
            try:
                builtin_roles.update({subscription: {}})
                custom_roles.update({subscription: {}})
                all_roles = client.role_definitions.list(
                    scope=f"/subscriptions/{self.subscriptions[subscription]}",
                )
                for role in all_roles:
                    if role.role_type == "CustomRole":
                        custom_roles[subscription][role.id] = Role(
                            id=role.id,
                            name=role.role_name,
                            type=role.role_type,
                            assignable_scopes=role.assignable_scopes,
                            permissions=[
                                Permission(
                                    condition=getattr(permission, "condition", ""),
                                    condition_version=getattr(
                                        permission, "condition_version", ""
                                    ),
                                    actions=getattr(permission, "actions", []),
                                )
                                for permission in getattr(role, "permissions", [])
                            ],
                        )
                    else:
                        builtin_roles[subscription][role.id] = Role(
                            id=role.id,
                            name=role.role_name,
                            type=role.role_type,
                            assignable_scopes=role.assignable_scopes,
                            permissions=role.permissions,
                        )
            except Exception as error:
                logger.error(
                    f"Subscription name: {subscription} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
                )
        return builtin_roles, custom_roles

    def _get_role_assignments(self):
        logger.info("IAM - Getting role assignments...")
        role_assignments = {}
        for subscription, client in self.clients.items():
            try:
                role_assignments.update({subscription: {}})
                all_role_assignments = client.role_assignments.list_for_subscription(
                    filter="atScope()"
                )
                for role_assignment in all_role_assignments:
                    role_assignments[subscription].update(
                        {
                            role_assignment.id: RoleAssignment(
                                id=role_assignment.id,
                                name=role_assignment.name,
                                scope=role_assignment.scope,
                                agent_id=role_assignment.principal_id,
                                agent_type=role_assignment.principal_type,
                                role_id=role_assignment.role_definition_id.split("/")[
                                    -1
                                ],
                            )
                        }
                    )
            except Exception as error:
                logger.error(
                    f"Subscription name: {subscription} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
                )
        return role_assignments


@dataclass
class Permission:
    actions: List[str]
    condition: str
    condition_version: str


@dataclass
class Role:
    id: str
    name: str
    type: str
    assignable_scopes: List[str]
    permissions: List[Permission]


@dataclass
class RoleAssignment:
    """
    Represents an Azure Role Assignment.

    Attributes:
        id: The unique identifier of the role assignment.
        name: The name of the role assignment.
        scope: The scope at which the role assignment applies.
        agent_id: The principal (user, group, service principal, etc.) ID assigned the role.
        agent_type: The type of the principal. Known values: "User", "Group", "ServicePrincipal", "ForeignGroup", and "Device".
        role_id: The ID of the role definition assigned.
    """

    id: str
    name: str
    scope: str
    agent_id: str
    agent_type: str
    role_id: str
