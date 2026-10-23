param([Parameter(Mandatory=$true)][string]$InputDocx,[Parameter(Mandatory=$true)][string]$OutputPdf)
$ErrorActionPreference='Stop'
$wordApp=$null
$wordDoc=$null
try {
  $wordApp=New-Object -ComObject Word.Application
  $wordApp.Visible=$false
  $wordApp.DisplayAlerts=0
  $wordApp.AutomationSecurity=3
  $wordDoc=$wordApp.Documents.Open($InputDocx,$false,$true)
  $wordDoc.Repaginate()
  $wordDoc.ExportAsFixedFormat($OutputPdf,17)
  Write-Output ('PAGES '+$wordDoc.ComputeStatistics(2))
} finally {
  if ($null -ne $wordDoc) {$wordDoc.Close(0)}
  if ($null -ne $wordApp) {$wordApp.Quit()}
}
