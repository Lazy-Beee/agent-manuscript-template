<#
.SYNOPSIS
  Pull one section out of a manuscript Markdown file into a standalone .md, for
  rendering a single section to .docx without touching the source.

  The section runs from its own heading to the next heading at the SAME level, so
  -Section "5" takes "# 5. ..." through everything under it (5.1, 5.1.1, ...) and
  stops at "# 6. ...", while -Section "5.1" takes "## 5.1 ..." and stops at "## 5.2 ...".
  Headings are copied verbatim, so figure/table numbers stay as they are in the full
  manuscript; a provenance line is inserted under the top heading to say so.

  -WithParentHeadings prepends the enclosing headings, so -Section 5.1 renders under its
  own "# 5. ..." title instead of starting cold at "## 5.1 ...". Only the headings are
  copied, not the prose under them.

.EXAMPLE
  .\extract_section.ps1 "{{DRAFT}}.md" -Section 5
  .\extract_section.ps1 "{{DRAFT}}.md" -Section 5.1 -WithParentHeadings
  .\extract_section.ps1 "{{DRAFT}}.md" -Section 5.1 -Output "sec 5.1.md"
  # then render it:
  ..\.claude\skills\manuscript-to-docx\scripts\render.ps1 "section 5.1 extract.md"
#>
param(
  [Parameter(Mandatory = $true)][string]$Manuscript,
  [Parameter(Mandatory = $true)][string]$Section,
  [string]$Output,
  [switch]$WithParentHeadings
)

$ErrorActionPreference = 'Stop'
$md = (Resolve-Path -LiteralPath $Manuscript).Path
$lines = Get-Content -LiteralPath $md -Encoding UTF8

# "5" -> "# 5." (top-level headings carry a dot), "5.1" -> "## 5.1 "
$depth = ($Section -split '\.').Count
$hashes = '#' * $depth
$pattern = if ($depth -eq 1) { "^$hashes $([regex]::Escape($Section))\. " }
           else { "^$hashes $([regex]::Escape($Section)) " }

$start = $lines | Select-String -Pattern $pattern | Select-Object -First 1
if (-not $start) { throw "section $Section not found (looked for /$pattern/)" }

# End at the next heading of the same depth, or EOF.
$sameLevel = "^$hashes [0-9]"
$after = $lines | Select-String -Pattern $sameLevel |
         Where-Object { $_.LineNumber -gt $start.LineNumber } | Select-Object -First 1
$endIdx = if ($after) { $after.LineNumber - 2 } else { $lines.Count - 1 }

# Enclosing headings, outermost first: for 5.1.2 that is "# 5. ..." then "## 5.1 ...".
$parents = @()
if ($WithParentHeadings) {
  $parts = $Section -split '\.'
  for ($d = 1; $d -lt $parts.Count; $d++) {
    $anc = ($parts[0..($d - 1)]) -join '.'
    $h = '#' * $d
    $ancPat = if ($d -eq 1) { "^$h $([regex]::Escape($anc))\. " } else { "^$h $([regex]::Escape($anc)) " }
    $hit = $lines | Select-String -Pattern $ancPat | Select-Object -First 1
    if ($hit) { $parents += @($hit.Line, '') }
  }
}

$note = "*Extract from ""$([IO.Path]::GetFileName($md))"" (Section $Section). " +
        "Figure, table and equation numbers follow the full manuscript.*"
$body = $parents + @($lines[($start.LineNumber - 1)], '', $note) + $lines[$start.LineNumber..$endIdx]
# The note belongs under the topmost heading, not buried under the section's own.
if ($parents.Count) {
  $body = @($parents[0], '', $note) + $parents[2..($parents.Count - 1)] +
          @($lines[($start.LineNumber - 1)]) + $lines[$start.LineNumber..$endIdx]
}

if (-not $Output) { $Output = Join-Path (Split-Path -Parent $md) "section $Section extract.md" }
$body | Set-Content -LiteralPath $Output -Encoding UTF8
Write-Host "OK -> $Output  ($($body.Count) lines)"
