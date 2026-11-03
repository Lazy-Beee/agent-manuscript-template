<#
.SYNOPSIS
  Render a manuscript Markdown file to .docx with the manuscript-to-docx Lua
  filters (mergecol.lua = merged group columns, eqnum.lua = right-aligned
  equation numbers, caption_style.lua = 10 pt figure/table captions with a bold
  label, refs_left.lua = left-aligned reference entries). Resolves the filters
  and the bundled reference doc relative to this script; pass -ReferenceDoc to
  override the reference doc.

  -Jpg converts the referenced PNG figures to JPG first (via jpgify.py) and
  renders from a rewritten copy, to shrink the .docx. The source .md and the
  original figures are left untouched. The rendered document ends with a note
  stating that its figures are compressed JPEGs; -NoJpgNote suppresses it.

.EXAMPLE
  .\render.ps1 "my paper draft.md"
  .\render.ps1 "my paper draft.md" -Output "my paper draft v2.docx"
  .\render.ps1 draft.md -ReferenceDoc house-style.docx
  .\render.ps1 draft.md -Jpg                       # smaller docx (JPEG q85, figures capped at 2600 px)
  .\render.ps1 draft.md -Jpg -JpgMaxWidth 0        # JPEG but keep full figure resolution
  .\render.ps1 draft.md -Jpg -JpgQuality 90 -JpgMaxWidth 2000
#>
param(
  [Parameter(Mandatory = $true)][string]$Manuscript,
  [string]$Output,
  [string]$ReferenceDoc,
  [switch]$Jpg,
  [int]$JpgQuality = 85,
  [int]$JpgMaxWidth = 2600,
  [switch]$NoJpgNote
)

$ErrorActionPreference = 'Stop'
$md = (Resolve-Path -LiteralPath $Manuscript).Path
$dir = Split-Path -Parent $md
if (-not $Output) { $Output = [IO.Path]::ChangeExtension($md, '.docx') }
$filters = Join-Path $PSScriptRoot '..\filters'

# Optional: convert PNGs to JPG and render from the rewritten copy.
$renderMd = $md
$staging = $null
if ($Jpg) {
  $staging = Join-Path ([IO.Path]::GetTempPath()) ('jpgify_' + [IO.Path]::GetRandomFileName())
  $jpgify = Join-Path $PSScriptRoot 'jpgify.py'
  $jpgArgs = @($jpgify, $md, '--quality', $JpgQuality, '--staging', $staging)
  if ($JpgMaxWidth -gt 0) { $jpgArgs += @('--max-width', $JpgMaxWidth) }
  if ($NoJpgNote) { $jpgArgs += '--no-note' }
  # jpgify writes its progress/summary to stderr and the rewritten-md path to stdout.
  # Relax EAP around the call so the stderr lines are not turned into terminating
  # NativeCommandErrors (PowerShell 5.1); merge with 2>&1, then split stdout
  # ([string]) from stderr (ErrorRecord) and echo the progress to the host.
  $prevEAP = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  $jpgOut = & python @jpgArgs 2>&1
  $jpgCode = $LASTEXITCODE
  $ErrorActionPreference = $prevEAP
  $jpgOut | Where-Object { $_ -isnot [string] } | ForEach-Object { Write-Host $_.ToString() }
  $renderMd = $jpgOut | Where-Object { $_ -is [string] } | Select-Object -Last 1
  if ($jpgCode -ne 0 -or -not $renderMd) {
    Write-Host "jpgify failed (exit $jpgCode)."
    exit 1
  }
}

# Reference doc: caller-supplied template wins; otherwise the bundled one, which
# defines the caption style (Figure/Table captions at 10 pt via caption_style.lua).
$assets = Join-Path $PSScriptRoot '..\assets'
if ($ReferenceDoc) {
  $refDoc = (Resolve-Path -LiteralPath $ReferenceDoc).Path
} else {
  $refDoc = (Resolve-Path -LiteralPath (Join-Path $assets 'reference.docx')).Path
}

$pandocArgs = @(
  $renderMd,
  # -implicit_figures: captions are explicit "Figure N." paragraphs, so a non-empty
  # image alt must not also become a pandoc figure caption (that doubles the caption).
  # The alt text is still kept as the image's accessibility descr.
  '--from=markdown+tex_math_dollars-implicit_figures',
  '--to=docx',
  "--resource-path=$dir",
  '--lua-filter', (Join-Path $filters 'mergecol.lua'),
  '--lua-filter', (Join-Path $filters 'eqnum.lua'),
  '--lua-filter', (Join-Path $filters 'caption_style.lua'),
  '--lua-filter', (Join-Path $filters 'refs_left.lua'),
  '--reference-doc', $refDoc,
  '-o', $Output
)

try {
  pandoc @pandocArgs
  $code = $LASTEXITCODE
  if ($code -eq 0) {
    $groupedTableFormatter = Join-Path $PSScriptRoot 'format_grouped_tables.py'
    & python $groupedTableFormatter $Output
    $code = $LASTEXITCODE
  }
}
finally {
  if ($staging -and (Test-Path -LiteralPath $staging)) {
    Remove-Item -LiteralPath $staging -Recurse -Force
  }
}

if ($code -eq 0) {
  Write-Host "OK -> $Output"
} else {
  Write-Host "Render failed (exit $code). If the target .docx is open in Word, close it and retry."
  exit $code
}
