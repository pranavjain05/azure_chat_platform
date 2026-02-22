provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "chat_rg" {
  name     = "chat-rg-tf"
  location = "Central India"
}

resource "azurerm_cosmosdb_account" "chat_cosmos" {
  name                = "chat-cosmos-pranav"
  location            = "Central India"
  resource_group_name = "chat-rg"
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  free_tier_enabled = true

  consistency_policy {
    consistency_level       = "Session"
    max_interval_in_seconds = 5
    max_staleness_prefix    = 100
  }

  geo_location {
    location          = "Central India"
    failover_priority = 0
  }

  lifecycle {
    ignore_changes = all
  }
}
resource "azurerm_cosmosdb_sql_database" "chat_db" {
  name                = "chatdb"
  resource_group_name = "chat-rg"
  account_name        = azurerm_cosmosdb_account.chat_cosmos.name
}

resource "azurerm_cosmosdb_sql_container" "messages" {
  name                = "messages"
  resource_group_name = "chat-rg"
  account_name        = azurerm_cosmosdb_account.chat_cosmos.name
  database_name       = azurerm_cosmosdb_sql_database.chat_db.name
  partition_key_paths = ["/conversationId"]

  lifecycle {
    ignore_changes = all
  }
}

resource "azurerm_linux_web_app" "chat_backend" {
  name                = "chat-backend-pranav"
  resource_group_name = "chat-rg"
  location            = "Central India"

  service_plan_id = "/subscriptions/b6d7105d-a695-49e3-a325-bd8c1d9f2dcd/resourceGroups/chat-rg/providers/Microsoft.Web/serverFarms/ASP-chatrg-bdec"

  site_config {}

  lifecycle {
    ignore_changes = all
  }
}