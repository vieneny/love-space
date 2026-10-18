#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackendOrigin,
    [string]$CloudflaredPath,
    [ValidateRange(10, 50)]
    [int]$TimeoutSeconds = 45,
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function ConvertTo-PrivateBackendOrigin {
    param([string]$Value)
    $match = [regex]::Match($Value, '^http://((?:0|[1-9][0-9]{0,2})(?:\.(?:0|[1-9][0-9]{0,2})){3})(?::([1-9][0-9]{0,4}))?/?$')
    if (-not $match.Success) {
        throw 'BackendOrigin 必须是规范的私网 IPv4 HTTP 源地址，不带账号、路径、查询参数或片段。'
    }
    $octets = @($match.Groups[1].Value.Split('.') | ForEach-Object { [int]$_ })
    $isPrivate = $octets[0] -eq 10 -or ($octets[0] -eq 172 -and $octets[1] -ge 16 -and $octets[1] -le 31) -or ($octets[0] -eq 192 -and $octets[1] -eq 168)
    if (@($octets | Where-Object { $_ -gt 255 }).Count -gt 0 -or -not $isPrivate -or ($match.Groups[2].Success -and [int]$match.Groups[2].Value -gt 65535)) {
        throw 'BackendOrigin 仅接受 10/8、172.16/12、192.168/16 私网 IPv4 与有效端口。'
    }
    $portSuffix = if ($match.Groups[2].Success) { ':' + $match.Groups[2].Value } else { '' }
    return 'http://' + $match.Groups[1].Value + $portSuffix
}

function Get-ProcessRecord {
    param([System.Diagnostics.Process]$Process, [string]$ExecutablePath, [string]$StdoutPath, [string]$StderrPath)
    $startedUtc = $Process.StartTime.ToUniversalTime()
    $actualExecutablePath = $Process.Path
    if (-not $actualExecutablePath) {
        $processInfo = Get-CimInstance -ClassName Win32_Process -Filter ('ProcessId = ' + $Process.Id) -ErrorAction Stop
        # Win32_Process serializes creation time with lower precision than Process.StartTime.
        if ($null -ne $processInfo -and [Math]::Abs(($processInfo.CreationDate.ToUniversalTime() - $startedUtc).Ticks) -lt [TimeSpan]::TicksPerMillisecond) {
            $actualExecutablePath = [string]$processInfo.ExecutablePath
        }
    }
    if (-not $actualExecutablePath) { throw '无法读取本次进程的实际路径，不能保存可靠定位。' }
    return [ordered]@{
        pid = $Process.Id
        startTimeUtc = $startedUtc.ToString('o')
        executablePath = $actualExecutablePath
        launchExecutablePath = $ExecutablePath
        stdoutPath = $StdoutPath
        stderrPath = $StderrPath
    }
}

function Test-RecordedProcessAlive {
    param($Record)
    if ($null -eq $Record) { return $false }
    if (-not $Record.pid -or -not $Record.startTimeUtc -or -not $Record.executablePath) { throw '已有状态文件缺少进程定位信息，请先人工核对。' }
    $candidate = Get-Process -Id ([int]$Record.pid) -ErrorAction SilentlyContinue
    if ($null -eq $candidate) { return $false }
    $recordedStart = if ($Record.startTimeUtc -is [DateTime]) { $Record.startTimeUtc } else { [DateTime]::Parse([string]$Record.startTimeUtc, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind) }
    $sameStart = $candidate.StartTime.ToUniversalTime().Ticks -eq $recordedStart.ToUniversalTime().Ticks
    if (-not $sameStart) { return $false }
    $candidatePath = $candidate.Path
    if (-not $candidatePath) {
        $candidateInfo = Get-CimInstance -ClassName Win32_Process -Filter ('ProcessId = ' + $candidate.Id) -ErrorAction Stop
        if ($null -eq $candidateInfo -or -not $candidateInfo.ExecutablePath -or
            [Math]::Abs(($candidateInfo.CreationDate.ToUniversalTime() - $candidate.StartTime.ToUniversalTime()).Ticks) -ge [TimeSpan]::TicksPerMillisecond) {
            throw '已有 PID 仍存活但身份暂时无法核对；不会将其视为已停止。'
        }
        $candidatePath = [string]$candidateInfo.ExecutablePath
    }
    $samePath = [string]::Equals($candidatePath, [string]$Record.executablePath, [StringComparison]::OrdinalIgnoreCase)
    return $sameStart -and $samePath
}

function Update-OwnedGatewayChildren {
    param(
        [System.Diagnostics.Process]$Launcher,
        [System.Collections.Generic.List[System.Diagnostics.Process]]$OwnedProcesses,
        $State,
        [string]$StdoutPath,
        [string]$StderrPath
    )
    # Windows venv python.exe can launch a second python.exe. Only follow this
    # launcher's descendants with the exact gateway module and start ordering.
    $parents = New-Object 'System.Collections.Generic.Queue[System.Diagnostics.Process]'
    $parents.Enqueue($Launcher)
    $visited = @{}
    while ($parents.Count -gt 0) {
        $parentProcess = $parents.Dequeue()
        if ($visited.ContainsKey($parentProcess.Id)) { continue }
        $visited[$parentProcess.Id] = $true
        $children = @(Get-CimInstance -ClassName Win32_Process -Filter ('ParentProcessId = ' + $parentProcess.Id) -ErrorAction Stop)
        foreach ($childInfo in $children) {
            if ([string]$childInfo.CommandLine -notmatch '(?i)(?:^|\s)-m\s+uvicorn\s+app\.preview_gateway:app(?:\s|$)' -or
                [IO.Path]::GetFileName([string]$childInfo.ExecutablePath) -ine 'python.exe') { continue }
            $childProcess = Get-Process -Id ([int]$childInfo.ProcessId) -ErrorAction SilentlyContinue
            if ($null -eq $childProcess) { continue }
            if ([Math]::Abs(($childInfo.CreationDate.ToUniversalTime() - $childProcess.StartTime.ToUniversalTime()).Ticks) -ge [TimeSpan]::TicksPerMillisecond) { continue }
            $childActualPath = $childProcess.Path
            if (-not $childActualPath) { $childActualPath = [string]$childInfo.ExecutablePath }
            if (-not [string]::Equals($childActualPath, [string]$childInfo.ExecutablePath, [StringComparison]::OrdinalIgnoreCase)) { continue }
            if ($childProcess.StartTime.ToUniversalTime() -lt $parentProcess.StartTime.ToUniversalTime()) { continue }
            if (@($OwnedProcesses | Where-Object { $_.Id -eq $childProcess.Id }).Count -eq 0) {
                $OwnedProcesses.Add($childProcess)
                $State.gatewayChildren = @($State.gatewayChildren) + @(Get-ProcessRecord $childProcess $childProcess.Path $StdoutPath $StderrPath)
            }
            $parents.Enqueue($childProcess)
        }
    }
}

function Save-PreviewState {
    param($State, [string]$RunStatePath, [string]$LatestStatePath)
    $json = $State | ConvertTo-Json -Depth 8
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($RunStatePath, $json + [Environment]::NewLine, $utf8)
    [IO.File]::WriteAllText($LatestStatePath, $json + [Environment]::NewLine, $utf8)
}

function Read-SharedPreviewLog {
    param([string]$Path)
    $logStream = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
    $logReader = New-Object IO.StreamReader($logStream, [Text.Encoding]::UTF8, $true)
    try { return $logReader.ReadToEnd() }
    finally { $logReader.Dispose(); $logStream.Dispose() }
}

function Test-PreviewHealth {
    param([string]$Origin, [int]$RequestTimeoutSeconds = 2)
    $client = $null
    $response = $null
    $handler = $null
    try {
        $handler = New-Object System.Net.Http.HttpClientHandler
        $handler.AllowAutoRedirect = $false
        $handler.UseCookies = $false
        $client = New-Object System.Net.Http.HttpClient($handler)
        $client.MaxResponseContentBufferSize = 4096
        $client.Timeout = [TimeSpan]::FromSeconds($RequestTimeoutSeconds)
        $request = $client.GetAsync($Origin + '/health')
        # Bound the caller's wait as well as HttpClient's timeout (including slow DNS).
        if (-not $request.Wait($RequestTimeoutSeconds * 1000)) { $client.CancelPendingRequests(); return $false }
        $response = $request.GetAwaiter().GetResult()
        if ([int]$response.StatusCode -ne 200) { return $false }
        $health = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json
        return $health.status -eq 'ok'
    } catch { return $false }
    finally {
        if ($null -ne $response) { $response.Dispose() }
        if ($null -ne $client) { $client.Dispose() }
        elseif ($null -ne $handler) { $handler.Dispose() }
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDirectory = Join-Path $repoRoot 'backend'
$pythonPath = Join-Path $backendDirectory '.venv\Scripts\python.exe'
$gatewayOrigin = 'http://127.0.0.1:18102'
$artifactRoot = Join-Path $repoRoot 'artifacts'
$latestStatePath = Join-Path $artifactRoot 'public-preview-state.json'
$launchLockPath = Join-Path $artifactRoot 'public-preview-launch.lock'
$ownedProcesses = New-Object 'System.Collections.Generic.List[System.Diagnostics.Process]'
$launchLock = $null
$state = $null
$runStatePath = $null
$gatewayLauncherProcess = $null
$failureReason = '启动未完成；请检查本次状态文件和日志。'
$succeeded = $false

try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw '此脚本仅用于 Windows。' }
    $BackendOrigin = ConvertTo-PrivateBackendOrigin $BackendOrigin
    if (-not $CloudflaredPath) { $CloudflaredPath = Join-Path $artifactRoot 'tools\cloudflared.exe' }
    $CloudflaredPath = [IO.Path]::GetFullPath($CloudflaredPath)
    if (-not (Test-Path -LiteralPath $CloudflaredPath -PathType Leaf)) { throw '未找到 cloudflared.exe；请从官方来源下载并校验后传入路径。' }
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) { throw '未找到 backend 的 Windows Python 虚拟环境；请先完成后端依赖安装。' }
    if (-not (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue)) { throw '缺少 Windows Get-NetTCPConnection，无法确认网关监听归属。' }
    if ($CheckOnly) {
        $succeeded = $true
        Write-Output '本地可执行文件路径和 BackendOrigin 格式检查通过；未启动网关或隧道，未验证后端开关。'
        return
    }
    Add-Type -AssemblyName System.Net.Http

    [IO.Directory]::CreateDirectory($artifactRoot) | Out-Null
    try { $launchLock = [IO.File]::Open($launchLockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None) }
    catch { throw '另一个外网预览启动流程仍在运行；本次未接管其进程。' }
    if (Test-Path -LiteralPath $latestStatePath -PathType Leaf) {
        try { $previous = Get-Content -LiteralPath $latestStatePath -Raw -Encoding UTF8 | ConvertFrom-Json }
        catch { throw '已有外网预览状态文件无法解析，请先人工核对，避免重复启动。' }
        $previousRecords = @($previous.gateway, $previous.tunnel)
        if ($previous.PSObject.Properties['gatewayLauncher']) { $previousRecords += @($previous.gatewayLauncher) }
        if ($previous.PSObject.Properties['gatewayChildren']) { $previousRecords += @($previous.gatewayChildren) }
        if (@($previousRecords | Where-Object { Test-RecordedProcessAlive $_ }).Count -gt 0) {
            throw '上次记录的网关或隧道仍在运行；请核对 artifacts/public-preview-state.json 后处理，不会自动停止旧进程。'
        }
    }
    if (@(Get-NetTCPConnection -LocalPort 18102 -State Listen -ErrorAction SilentlyContinue).Count -gt 0) {
        throw '18102 已有监听进程；不会停止或复用该进程。'
    }

    $runId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
    $runDirectory = Join-Path $artifactRoot ('public-preview\' + $runId)
    [IO.Directory]::CreateDirectory($runDirectory) | Out-Null
    $runStatePath = Join-Path $runDirectory 'state.json'
    $gatewayStdout = Join-Path $runDirectory 'gateway.stdout.log'
    $gatewayStderr = Join-Path $runDirectory 'gateway.stderr.log'
    $tunnelStdout = Join-Path $runDirectory 'tunnel.stdout.log'
    $tunnelStderr = Join-Path $runDirectory 'tunnel.stderr.log'
    $state = [ordered]@{
        formatVersion = 2; runId = $runId; startedAtUtc = [DateTime]::UtcNow.ToString('o')
        status = 'starting'; backendOrigin = $BackendOrigin; gatewayOrigin = $gatewayOrigin
        publicUrl = $null; gatewayLauncher = $null; gatewayChildren = @(); gateway = $null; tunnel = $null; failureReason = $null
        failureCode = $null; failureLine = $null; failureType = $null
    }
    $timer = [Diagnostics.Stopwatch]::StartNew()

    $previousUpstream = [Environment]::GetEnvironmentVariable('PREVIEW_API_UPSTREAM', 'Process')
    try {
        [Environment]::SetEnvironmentVariable('PREVIEW_API_UPSTREAM', $BackendOrigin, 'Process')
        # FilePath/WorkingDirectory/redirection are separate parameters; do not invoke cmd.exe or interpolate paths into shell code.
        $gatewayLauncherProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'uvicorn', 'app.preview_gateway:app', '--host', '127.0.0.1', '--port', '18102', '--no-access-log') -WorkingDirectory $backendDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput $gatewayStdout -RedirectStandardError $gatewayStderr
        $ownedProcesses.Add($gatewayLauncherProcess)
    } finally {
        [Environment]::SetEnvironmentVariable('PREVIEW_API_UPSTREAM', $previousUpstream, 'Process')
    }
    $state.gatewayLauncher = Get-ProcessRecord $gatewayLauncherProcess $pythonPath $gatewayStdout $gatewayStderr
    Save-PreviewState $state $runStatePath $latestStatePath

    $gatewayReady = $false
    while ($timer.Elapsed.TotalSeconds -lt [Math]::Min(15, $TimeoutSeconds)) {
        Update-OwnedGatewayChildren $gatewayLauncherProcess $ownedProcesses $state $gatewayStdout $gatewayStderr
        Save-PreviewState $state $runStatePath $latestStatePath
        $listeners = @(Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 18102 -State Listen -ErrorAction SilentlyContinue)
        $listeningProcessIds = @($listeners | ForEach-Object { $_.OwningProcess })
        $gatewayCandidates = @($ownedProcesses | Where-Object { $_.Id -in $listeningProcessIds })
        if ($gatewayCandidates.Count -eq 1 -and (Test-PreviewHealth $gatewayOrigin)) {
            $gatewayProcess = $gatewayCandidates[0]
            $state.gateway = Get-ProcessRecord $gatewayProcess $pythonPath $gatewayStdout $gatewayStderr
            Save-PreviewState $state $runStatePath $latestStatePath
            $gatewayReady = $true
            break
        }
        $gatewayLauncherProcess.Refresh()
        if ($gatewayLauncherProcess.HasExited) { throw '本次网关启动器已退出且没有就绪的本次服务进程，请查看 gateway.stderr.log。' }
        Start-Sleep -Milliseconds 250
    }
    if (-not $gatewayReady) { throw '网关或源后端未在时限内通过 /health 检查，未启动隧道。' }

    $tunnelProcess = Start-Process -FilePath $CloudflaredPath -ArgumentList @('tunnel', '--no-autoupdate', '--protocol', 'http2', '--url', $gatewayOrigin) -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $tunnelStdout -RedirectStandardError $tunnelStderr
    $ownedProcesses.Add($tunnelProcess)
    $state.tunnel = Get-ProcessRecord $tunnelProcess $CloudflaredPath $tunnelStdout $tunnelStderr
    Save-PreviewState $state $runStatePath $latestStatePath

    while ($timer.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        $gatewayProcess.Refresh()
        $tunnelProcess.Refresh()
        if ($gatewayProcess.HasExited -or $tunnelProcess.HasExited) { throw '本次网关或隧道进程已退出，请查看本次日志。' }
        $logText = ''
        foreach ($logPath in @($tunnelStdout, $tunnelStderr)) {
            if (Test-Path -LiteralPath $logPath -PathType Leaf) { $logText += Read-SharedPreviewLog $logPath }
        }
        $urls = [regex]::Matches($logText, 'https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.trycloudflare\.com\b', [Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if ($urls.Count -gt 0) {
            $candidateUrl = $urls[$urls.Count - 1].Value.ToLowerInvariant()
            if (Test-PreviewHealth $candidateUrl 3) {
                $state.publicUrl = $candidateUrl
                $state.status = 'ready'
                Save-PreviewState $state $runStatePath $latestStatePath
                $succeeded = $true
                Write-Output ('Gateway PID: ' + $gatewayProcess.Id)
                Write-Output ('Tunnel PID: ' + $tunnelProcess.Id)
                Write-Output ('Public URL: ' + $candidateUrl)
                Write-Output ('State: ' + $latestStatePath)
                Write-Output '仅为临时开发预览；保持电脑、源后端、网关和隧道运行。地址变化后需重新生成微信预览二维码。'
                break
            }
        }
        Start-Sleep -Milliseconds 300
    }
    if (-not $succeeded) { throw '未在时限内获得通过 /health 验证的临时 HTTPS 地址。' }
} catch {
    # Do not dump exception objects, process environments or gateway/tunnel logs into the console.
    if ($_.Exception -is [System.Management.Automation.RuntimeException] -and $_.Exception.Message -eq [string]$_.TargetObject) {
        $failureReason = $_.Exception.Message
    }
    if ($null -ne $state) {
        $state.status = 'failed'
        $state.failureReason = $failureReason
        $state.failureCode = $_.FullyQualifiedErrorId
        $state.failureLine = $_.InvocationInfo.ScriptLineNumber
        $state.failureType = $_.Exception.GetType().FullName
    }
    Write-Error $failureReason -ErrorAction Continue
} finally {
    if (-not $succeeded) {
        if ($null -ne $gatewayLauncherProcess -and $null -ne $state) {
            try { Update-OwnedGatewayChildren $gatewayLauncherProcess $ownedProcesses $state $gatewayStdout $gatewayStderr }
            catch { $state.failureReason = '子进程核对未完全成功，请按状态文件核对本次启动器与服务进程。' }
        }
        for ($ownedIndex = $ownedProcesses.Count - 1; $ownedIndex -ge 0; $ownedIndex--) {
            try {
                $owned = $ownedProcesses[$ownedIndex]
                $owned.Refresh()
                if (-not $owned.HasExited) {
                    $identityRecords = @($state.gatewayLauncher, $state.gateway, $state.tunnel) + @($state.gatewayChildren)
                    $ownedRecord = @($identityRecords | Where-Object { $null -ne $_ -and $_.pid -eq $owned.Id } | Select-Object -First 1)
                    if ($ownedRecord.Count -ne 1) { throw '本次进程缺少已核实身份，跳过自动结束。' }
                    if (Test-RecordedProcessAlive $ownedRecord[0]) { $owned.Kill(); [void]$owned.WaitForExit(2000) }
                }
            } catch {
                if ($null -ne $state) { $state.failureReason = '本次进程清理未完全成功，请按状态文件核对 PID 和启动时间。' }
            }
        }
        if ($null -ne $state -and $runStatePath) {
            try { Save-PreviewState $state $runStatePath $latestStatePath }
            catch { Write-Warning '无法保存本次状态；请检查 artifacts 目录权限。' }
        }
    }
    if ($null -ne $launchLock) {
        $launchLock.Dispose()
        Remove-Item -LiteralPath $launchLockPath -Force -ErrorAction SilentlyContinue
    }
}
if (-not $succeeded) { exit 1 }
