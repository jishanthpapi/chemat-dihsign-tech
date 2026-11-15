# Generated caches in this OneDrive checkout retained read-only native libraries.
# Clear only that attribute in this checkout's generated Flutter build cache.
$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$expectedBuildCache = Join-Path $repositoryRoot 'mobile\build'
if (-not (Test-Path -LiteralPath $expectedBuildCache)) {
    Write-Output 'No generated Flutter build cache to prepare.'
    return
}
$buildCache = Get-Item -LiteralPath $expectedBuildCache
if ($buildCache.FullName -ne $expectedBuildCache -or
    $buildCache.LinkType -in @('Junction', 'SymbolicLink')) {
    throw 'Unexpected Flutter build cache path.'
}
$prepared = 0
$items = @(Get-ChildItem -LiteralPath $buildCache.FullName -Recurse -Force)
$items += $buildCache
foreach ($item in $items) {
    if ($item.LinkType -in @('Junction', 'SymbolicLink')) { continue }
    if ($item.Attributes -band [System.IO.FileAttributes]::ReadOnly) {
        $item.Attributes = $item.Attributes -band (-bnot [System.IO.FileAttributes]::ReadOnly)
        $prepared++
    }
}
Write-Output "Cleared read-only attributes on $prepared generated build entries. No files deleted."
