// ------------------
//    PARAMETERS
// ------------------

@description('Location to be used for resources. Defaults to the resource group location')
param location string = resourceGroup().location

@description('The unique suffix to append. Defaults to a unique string based on subscription and resource group IDs.')
param resourceSuffix string = uniqueString(subscription().id, resourceGroup().id)

param apimName string = 'apim-${resourceSuffix}'
param appInsightsName string = 'appi-${resourceSuffix}'
param apis array = []

@description('Base URL for the deployed SSE backend, for example https://myapp.some-region.azurecontainerapps.io')
param backendUrl string

// ------------------
//    RESOURCES
// ------------------

// Existing App Insights (created by infra)
resource appInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: appInsightsName
}

var appInsightsId = appInsights.id
var appInsightsInstrumentationKey = appInsights.properties.InstrumentationKey

// Existing APIM (created by infra)
resource apimService 'Microsoft.ApiManagement/service@2024-06-01-preview' existing = {
  name: apimName
}

// APIM backend that points to the SSE container app
module backendModule '../../shared/bicep/modules/apim/v1/backend.bicep' = {
  name: 'sse-backend'
  params: {
    apimName: apimName
    backendName: 'sse-backend'
    url: backendUrl
  }
  dependsOn: [
    apimService
  ]
}

// APIM APIs
// NOTE: For SSE, do NOT enable request/response body logging.
// The shared api module creates diagnostics if App Insights params are set,
// so we intentionally pass empty strings here.
module apisModule '../../shared/bicep/modules/apim/v1/api.bicep' = [
  for api in apis: if (!empty(apis)) {
    name: 'api-${api.name}'
    params: {
      apimName: apimName
      appInsightsInstrumentationKey: ''
      appInsightsId: ''
      api: api
    }
    dependsOn: [
      apimService
      backendModule
    ]
  }
]

// ------------------
//    MARK: OUTPUTS
// ------------------

output apimServiceId string = apimService.id
output apimServiceName string = apimService.name
output apimResourceGatewayURL string = apimService.properties.gatewayUrl

output backendName string = backendModule.outputs.backendName
output backendUrlOut string = backendUrl

output apiOutputs array = [
  for i in range(0, length(apis)): {
    name: apis[i].name
    resourceId: apisModule[i].?outputs.?apiResourceId ?? ''
    displayName: apisModule[i].?outputs.?apiDisplayName ?? ''
    subscriptionResourceId: apisModule[i].?outputs.?subscriptionResourceId ?? ''
    subscriptionName: apisModule[i].?outputs.?subscriptionName ?? ''
    subscriptionPrimaryKey: apisModule[i].?outputs.?subscriptionPrimaryKey ?? ''
    subscriptionSecondaryKey: apisModule[i].?outputs.?subscriptionSecondaryKey ?? ''
  }
]
