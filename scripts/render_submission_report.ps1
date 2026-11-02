param([string]$ProjectRoot = 'C:\Users\Arman Acharya\OneDrive\Desktop\PricePilot')
$ErrorActionPreference = 'Stop'
$reportDocx = Join-Path $ProjectRoot 'output\submission\PricePilot_Project_Documentation.docx'
$reportPdf = Join-Path $ProjectRoot 'output\submission\PricePilot_Project_Documentation.pdf'
$wordInstance = $null
$reportDocument = $null
try {
    $wordInstance = New-Object -ComObject Word.Application
    $wordInstance.Visible = $false
    $wordInstance.DisplayAlerts = 0
    $reportDocument = $wordInstance.Documents.Open($reportDocx, $false, $false)
    $reportDocument.Fields.Update() | Out-Null
    foreach ($contentsTable in $reportDocument.TablesOfContents) { $contentsTable.Update() }
    $reportDocument.Repaginate()
    foreach ($contentsTable in $reportDocument.TablesOfContents) { $contentsTable.UpdatePageNumbers() }
    $reportDocument.Save()
    $reportDocument.ExportAsFixedFormat($reportPdf, 17)
    Write-Output ('Word rendered pages: ' + $reportDocument.ComputeStatistics(2))
    Write-Output $reportPdf
}
finally {
    if ($null -ne $reportDocument) { $reportDocument.Close(0); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($reportDocument) }
    if ($null -ne $wordInstance) { $wordInstance.Quit(); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordInstance) }
}
