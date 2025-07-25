from unittest import mock
from uuid import uuid4

from prowler.providers.azure.services.storage.storage_service import (
    Account,
    NetworkRuleSet,
)
from tests.providers.azure.azure_fixtures import (
    AZURE_SUBSCRIPTION_ID,
    set_mocked_azure_provider,
)


class Test_storage_blob_public_access_level_is_disabled:
    def test_storage_no_storage_accounts(self):
        storage_client = mock.MagicMock
        storage_client.storage_accounts = {}

        with (
            mock.patch(
                "prowler.providers.common.provider.Provider.get_global_provider",
                return_value=set_mocked_azure_provider(),
            ),
            mock.patch(
                "prowler.providers.azure.services.storage.storage_blob_public_access_level_is_disabled.storage_blob_public_access_level_is_disabled.storage_client",
                new=storage_client,
            ),
        ):
            from prowler.providers.azure.services.storage.storage_blob_public_access_level_is_disabled.storage_blob_public_access_level_is_disabled import (
                storage_blob_public_access_level_is_disabled,
            )

            check = storage_blob_public_access_level_is_disabled()
            result = check.execute()
            assert len(result) == 0

    def test_storage_storage_accounts_public_access_level_enabled(self):
        storage_account_id = str(uuid4())
        storage_account_name = "Test Storage Account"
        storage_client = mock.MagicMock
        storage_client.storage_accounts = {
            AZURE_SUBSCRIPTION_ID: [
                Account(
                    id=storage_account_id,
                    name=storage_account_name,
                    resouce_group_name="rg",
                    enable_https_traffic_only=False,
                    infrastructure_encryption=False,
                    network_rule_set=NetworkRuleSet(
                        bypass="AzureServices", default_action="Allow"
                    ),
                    encryption_type="None",
                    minimum_tls_version="TLS1_2",
                    private_endpoint_connections=[],
                    allow_blob_public_access=True,
                    key_expiration_period_in_days=None,
                    location="westeurope",
                )
            ]
        }

        with (
            mock.patch(
                "prowler.providers.common.provider.Provider.get_global_provider",
                return_value=set_mocked_azure_provider(),
            ),
            mock.patch(
                "prowler.providers.azure.services.storage.storage_blob_public_access_level_is_disabled.storage_blob_public_access_level_is_disabled.storage_client",
                new=storage_client,
            ),
        ):
            from prowler.providers.azure.services.storage.storage_blob_public_access_level_is_disabled.storage_blob_public_access_level_is_disabled import (
                storage_blob_public_access_level_is_disabled,
            )

            check = storage_blob_public_access_level_is_disabled()
            result = check.execute()
            assert len(result) == 1
            assert result[0].status == "FAIL"
            assert (
                result[0].status_extended
                == f"Storage account {storage_account_name} from subscription {AZURE_SUBSCRIPTION_ID} has allow blob public access enabled."
            )
            assert result[0].subscription == AZURE_SUBSCRIPTION_ID
            assert result[0].resource_name == storage_account_name
            assert result[0].resource_id == storage_account_id
            assert result[0].location == "westeurope"

    def test_storage_storage_accounts_public_access_level_disabled(self):
        storage_account_id = str(uuid4())
        storage_account_name = "Test Storage Account"
        storage_client = mock.MagicMock
        storage_client.storage_accounts = {
            AZURE_SUBSCRIPTION_ID: [
                Account(
                    id=storage_account_id,
                    name=storage_account_name,
                    resouce_group_name="rg",
                    enable_https_traffic_only=False,
                    infrastructure_encryption=False,
                    network_rule_set=NetworkRuleSet(
                        bypass="AzureServices", default_action="Allow"
                    ),
                    encryption_type="None",
                    minimum_tls_version="TLS1_2",
                    private_endpoint_connections=[],
                    allow_blob_public_access=False,
                    key_expiration_period_in_days=None,
                    location="westeurope",
                )
            ]
        }

        with (
            mock.patch(
                "prowler.providers.common.provider.Provider.get_global_provider",
                return_value=set_mocked_azure_provider(),
            ),
            mock.patch(
                "prowler.providers.azure.services.storage.storage_blob_public_access_level_is_disabled.storage_blob_public_access_level_is_disabled.storage_client",
                new=storage_client,
            ),
        ):
            from prowler.providers.azure.services.storage.storage_blob_public_access_level_is_disabled.storage_blob_public_access_level_is_disabled import (
                storage_blob_public_access_level_is_disabled,
            )

            check = storage_blob_public_access_level_is_disabled()
            result = check.execute()
            assert len(result) == 1
            assert result[0].status == "PASS"
            assert (
                result[0].status_extended
                == f"Storage account {storage_account_name} from subscription {AZURE_SUBSCRIPTION_ID} has allow blob public access disabled."
            )
            assert result[0].subscription == AZURE_SUBSCRIPTION_ID
            assert result[0].resource_name == storage_account_name
            assert result[0].resource_id == storage_account_id
            assert result[0].location == "westeurope"
