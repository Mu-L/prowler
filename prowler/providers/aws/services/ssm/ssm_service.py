import json
import time
from enum import Enum
from typing import Optional

from botocore.client import ClientError
from pydantic.v1 import BaseModel

from prowler.lib.logger import logger
from prowler.lib.scan_filters.scan_filters import is_resource_filtered
from prowler.providers.aws.lib.service.service import AWSService


class SSM(AWSService):
    def __init__(self, provider):
        # Call AWSService's __init__
        super().__init__(__class__.__name__, provider)
        self.documents = {}
        self.compliance_resources = {}
        self.managed_instances = {}
        self.__threading_call__(self._list_documents)
        self.__threading_call__(self._get_document)
        self.__threading_call__(self._describe_document_permission)
        self.__threading_call__(self._list_resource_compliance_summaries)
        self.__threading_call__(self._describe_instance_information)

    def _list_documents(self, regional_client):
        logger.info("SSM - Listing Documents...")
        try:
            # To retrieve only the documents owned by the account
            list_documents_parameters = {
                "Filters": [
                    {
                        "Key": "Owner",
                        "Values": [
                            "Self",
                        ],
                    },
                ],
            }
            list_documents_paginator = regional_client.get_paginator("list_documents")
            for page in list_documents_paginator.paginate(**list_documents_parameters):
                for document in page["DocumentIdentifiers"]:
                    document_name = document["Name"]
                    document_arn = f"arn:{self.audited_partition}:ssm:{regional_client.region}:{self.audited_account}:document/{document_name}"
                    if not self.audit_resources or (
                        is_resource_filtered(document_arn, self.audit_resources)
                    ):
                        # We must use the Document ARN as the dict key to have unique keys
                        self.documents[document_arn] = Document(
                            arn=document_arn,
                            name=document_name,
                            region=regional_client.region,
                            tags=document.get("Tags"),
                        )

        except Exception as error:
            logger.error(
                f"{regional_client.region} --"
                f" {error.__class__.__name__}[{error.__traceback__.tb_lineno}]:"
                f" {error}"
            )

    def _get_document(self, regional_client):
        logger.info("SSM - Getting Document...")
        for document in self.documents.values():
            try:
                if document.region == regional_client.region:
                    document_info = regional_client.get_document(Name=document.name)
                    self.documents[document.arn].content = json.loads(
                        document_info["Content"]
                    )

            except ClientError as error:
                if error.response["Error"]["Code"] == "ValidationException":
                    logger.warning(
                        f"{regional_client.region} --"
                        f" {error.__class__.__name__}[{error.__traceback__.tb_lineno}]:"
                        f" {error}"
                    )
                    continue

            except Exception as error:
                logger.error(
                    f"{regional_client.region} --"
                    f" {error.__class__.__name__}[{error.__traceback__.tb_lineno}]:"
                    f" {error}"
                )

    def _describe_document_permission(self, regional_client):
        logger.info("SSM - Describing Document Permission...")
        try:
            for document in self.documents.values():
                if document.region == regional_client.region:
                    document_permissions = regional_client.describe_document_permission(
                        Name=document.name, PermissionType="Share"
                    )
                    self.documents[document.arn].account_owners = document_permissions[
                        "AccountIds"
                    ]

        except ClientError as error:
            if error.response["Error"]["Code"] in [
                "InvalidDocumentOperation",
            ]:
                logger.warning(
                    f"{regional_client.region} --"
                    f" {error.__class__.__name__}[{error.__traceback__.tb_lineno}]:"
                    f" {error}"
                )
            else:
                logger.error(
                    f"{regional_client.region} --"
                    f" {error.__class__.__name__}[{error.__traceback__.tb_lineno}]:"
                    f" {error}"
                )
        except Exception as error:
            logger.error(
                f"{regional_client.region} --"
                f" {error.__class__.__name__}[{error.__traceback__.tb_lineno}]:"
                f" {error}"
            )

    def _list_resource_compliance_summaries(self, regional_client):
        logger.info("SSM - List Resources Compliance Summaries...")
        try:
            list_resource_compliance_summaries_paginator = (
                regional_client.get_paginator("list_resource_compliance_summaries")
            )
            for page in list_resource_compliance_summaries_paginator.paginate():
                for item in page["ResourceComplianceSummaryItems"]:
                    resource_id = item["ResourceId"]
                    resource_arn = f"arn:{self.audited_partition}:ec2:{regional_client.region}:{self.audited_account}:instance/{resource_id}"
                    if not self.audit_resources or (
                        is_resource_filtered(resource_arn, self.audit_resources)
                    ):
                        resource_status = item["Status"]

                        self.compliance_resources[resource_id] = ComplianceResource(
                            id=resource_id,
                            arn=resource_arn,
                            status=resource_status,
                            region=regional_client.region,
                        )

        except Exception as error:
            logger.error(
                f"{regional_client.region} --"
                f" {error.__class__.__name__}[{error.__traceback__.tb_lineno}]:"
                f" {error}"
            )

    def _describe_instance_information(self, regional_client):
        logger.info("SSM - Describing Instance Information...")
        try:
            describe_instance_information_paginator = regional_client.get_paginator(
                "describe_instance_information"
            )
            for page in describe_instance_information_paginator.paginate():
                for item in page["InstanceInformationList"]:
                    resource_id = item["InstanceId"]
                    resource_arn = f"arn:{self.audited_partition}:ec2:{regional_client.region}:{self.audited_account}:instance/{resource_id}"
                    self.managed_instances[resource_id] = ManagedInstance(
                        arn=resource_arn,
                        id=resource_id,
                        region=regional_client.region,
                    )
                # boto3 does not properly handle throttling exceptions for
                # ssm:DescribeInstanceInformation when there are large numbers of instances
                # AWS support recommends manually reducing frequency of requests
                time.sleep(0.1)

        except Exception as error:
            logger.error(
                f"{regional_client.region} --"
                f" {error.__class__.__name__}[{error.__traceback__.tb_lineno}]:"
                f" {error}"
            )


class ResourceStatus(Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"


class ComplianceResource(BaseModel):
    id: str
    arn: str
    region: str
    status: ResourceStatus


class Document(BaseModel):
    arn: str
    name: str
    region: str
    content: dict = None
    account_owners: list[str] = None
    tags: Optional[list] = []


class ManagedInstance(BaseModel):
    arn: str
    id: str
    region: str
