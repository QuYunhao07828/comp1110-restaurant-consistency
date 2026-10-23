param([Parameter(Mandatory=$true)][string]$Uri,[Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$downloadResponse = Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $OutputPath -PassThru -TimeoutSec 90 -UserAgent 'COMP1110-RestaurantConsistency/0.1 academic public-data pilot'
$responseHeaders = @{}
foreach ($headerName in $downloadResponse.Headers.Keys) { $responseHeaders[$headerName] = [string]$downloadResponse.Headers[$headerName] }
@{ status=[int]$downloadResponse.StatusCode; headers=$responseHeaders } | ConvertTo-Json -Compress -Depth 5
