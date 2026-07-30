# Kill Python worker processes whose parent no longer exists.
#
# Every multiprocessing pool in this project can leave its children behind when
# the parent dies badly - a killed run, a BrokenProcessPool, a frozen terminal.
# Those children keep a full CPU core each and are invisible unless you go
# looking: 39 of them were found alive one night, some for hours, and they are
# the reason the desktop kept freezing. This has now happened three times, so it
# is a script rather than a habit.
#
# Only processes that are BOTH multiprocessing children AND parentless are
# touched, so a healthy running job is never disturbed.
#
#   powershell -NoProfile -File reap_orphans.ps1          # report only
#   powershell -NoProfile -File reap_orphans.ps1 -Kill    # actually reap

param([switch]$Kill)

$all = Get-CimInstance Win32_Process -Filter "Name='python3.13.exe' OR Name='python.exe'"
$live = @{}
foreach ($p in $all) { $live[[int]$p.ProcessId] = $true }

$orphans = @()
foreach ($p in $all) {
    # multiprocessing children identify themselves in their command line
    if ($p.CommandLine -notmatch 'multiprocessing-fork|spawn_main') { continue }
    $ppid = [int]$p.ParentProcessId
    if (-not $live.ContainsKey($ppid)) { $orphans += $p }
}

# Also reap ABANDONED JOB TREES: a vdw_probe.py or cross_check.py whose own parent
# (the orchestrator) is gone. Its workers are NOT parentless -- the job parent is
# still alive -- so the multiprocessing-child test above misses them entirely, and
# they keep four cores busy on a question nobody is waiting for. This was found
# after stopping an orchestrator left its probe grinding on a superseded n for 45
# minutes, putting the machine at 6 workers against a cap of 4.
$jobs = Get-CimInstance Win32_Process -Filter "Name='python3.13.exe' OR Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'vdw_probe|cross_check' } |
    Where-Object { -not (Get-Process -Id $_.ParentProcessId -ErrorAction SilentlyContinue) }

if ($jobs) {
    Write-Output ("abandoned job trees: {0} (their launcher is gone)" -f @($jobs).Count)
    foreach ($j in $jobs) {
        $kids = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $j.ProcessId }
        Write-Output ("  pid {0} with {1} worker(s)" -f $j.ProcessId, @($kids).Count)
        if ($Kill) {
            foreach ($k in $kids) { Stop-Process -Id $k.ProcessId -Force -ErrorAction SilentlyContinue }
            Stop-Process -Id $j.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    if (-not $Kill) { Write-Output "run with -Kill to reap them" }
}

if ($orphans.Count -eq 0) {
    Write-Output "no orphaned workers"
    exit 0
}

$mb = [math]::Round((($orphans | Measure-Object WorkingSetSize -Sum).Sum) / 1MB)
Write-Output ("orphaned workers: {0}  (~{1} MB, parents already gone)" -f $orphans.Count, $mb)
foreach ($p in $orphans) {
    Write-Output ("  pid {0}  parent {1} (dead)" -f $p.ProcessId, $p.ParentProcessId)
}

if ($Kill) {
    foreach ($p in $orphans) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    Write-Output ("reaped {0}" -f $orphans.Count)
} else {
    Write-Output "run with -Kill to reap them"
}
