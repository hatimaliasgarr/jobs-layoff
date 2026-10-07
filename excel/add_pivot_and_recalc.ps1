# Step 5b - runs Microsoft Excel to:
#   1. add a "Pivot" sheet: PivotTable (Industry x Reason, sum of jobs cut) + 3 slicers
#   2. fully recalculate every formula (openpyxl writes formulas without cached values)
#   3. scan every sheet for formula errors (#N/A, #VALUE!, #REF!, #DIV/0!, #NAME?)
# Run:  powershell -ExecutionPolicy Bypass -File excel/add_pivot_and_recalc.ps1

$path = Join-Path $PSScriptRoot "AI_Layoffs_2026_Analysis.xlsx"
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Open($path)

    # ---------- PivotTable
    $data = $wb.Worksheets.Item("Data")
    $pv = $wb.Worksheets.Add([Type]::Missing, $wb.Worksheets.Item("Dashboard"))
    $pv.Name = "Pivot"
    $xl.ActiveWindow.DisplayGridlines = $false
    $cache = $wb.PivotCaches().Create(1, "tblLayoffs")          # 1 = xlDatabase
    $pt = $cache.CreatePivotTable($pv.Range("B6"), "ptReasonByIndustry")
    $pt.RowAxisLayout(1)                                        # tabular
    $pt.PivotFields("industry").Orientation = 1                  # rows
    $pt.PivotFields("category_label").Orientation = 2            # columns
    $f = $pt.AddDataField($pt.PivotFields("people_cut"), "Jobs cut", -4157)  # xlSum
    $f.NumberFormat = "#,##0"
    $pt.PivotFields("industry").AutoSort(2, "Jobs cut")          # descending by jobs
    $pt.TableStyle2 = "PivotStyleLight16"
    $pt.PivotFields("industry").Caption = "Industry"
    $pt.PivotFields("category_label").Caption = "Stated reason"

    # ---------- Slicers
    $sc1 = $wb.SlicerCaches.Add2($pt, "sector_group")
    $null = $sc1.Slicers.Add($pv, [Type]::Missing, "slSector", "Sector", 90, 800, 160, 110)
    $sc2 = $wb.SlicerCaches.Add2($pt, "company_size_band")
    $null = $sc2.Slicers.Add($pv, [Type]::Missing, "slSize", "Company size", 210, 800, 160, 170)
    $sc3 = $wb.SlicerCaches.Add2($pt, "severity_band")
    $null = $sc3.Slicers.Add($pv, [Type]::Missing, "slSeverity", "Share of workforce cut", 390, 800, 160, 170)

    $pv.Range("B2").Value2 = "PivotTable - jobs cut by industry and stated reason"
    $pv.Range("B2").Font.Bold = $true
    $pv.Range("B2").Font.Size = 16
    $pv.Range("B3").Value2 = "Use the slicers on the right to filter by sector, company size and severity."
    $pv.Range("B3").Font.Italic = $true

    # ---------- Recalculate + error scan
    $xl.CalculateFull()
    $errors = 0
    foreach ($ws in $wb.Worksheets) {
        try {
            $errCells = $ws.UsedRange.SpecialCells(-4123, 16)   # xlCellTypeFormulas, xlErrors
            $errors += $errCells.Count
            Write-Output ("ERRORS on {0}: {1}" -f $ws.Name, $errCells.Address())
        } catch { }                                            # no error cells -> exception, which is fine
    }
    $formulas = 0
    foreach ($ws in $wb.Worksheets) {
        try { $formulas += $ws.UsedRange.SpecialCells(-4123).Count } catch { }
    }
    $dash = $wb.Worksheets.Item("Dashboard")
    Write-Output ("Formulas: {0}  Errors: {1}" -f $formulas, $errors)
    Write-Output ("Dashboard check -> events {0}, jobs {1}, AI jobs {2}, AI share {3:P1}, total check {4}" -f `
        $dash.Range("C8").Value2, $dash.Range("D8").Value2, $dash.Range("E8").Value2, $dash.Range("F8").Value2, $dash.Range("D18").Value2)

    $dash.Activate()
    $wb.Save()
    $wb.Close($false)
}
finally {
    $xl.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
