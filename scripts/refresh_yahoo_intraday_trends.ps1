param(
  [string]$DataDir = (Join-Path $PSScriptRoot '..\data'),
  [string]$SourceConfig = (Join-Path $PSScriptRoot '..\data_sources.json')
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$manifestPath = Join-Path $DataDir 'manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$config = Get-Content -LiteralPath $SourceConfig -Raw -Encoding UTF8 | ConvertFrom-Json

function ConvertTo-UnixSecondsUtc([datetime]$Date) {
  $utc = [datetime]::SpecifyKind($Date, [DateTimeKind]::Utc)
  return [DateTimeOffset]::new($utc).ToUnixTimeSeconds()
}

function Get-EtfYahooSymbol([string]$Code) {
  if ($Code.StartsWith('5')) {
    return "$Code.SS"
  }
  return "$Code.SZ"
}

function Downsample-Points($Points, [int]$MaxPoints = 64) {
  if ($Points.Count -le $MaxPoints) {
    return @($Points)
  }
  $step = ($Points.Count - 1) / ($MaxPoints - 1)
  $sampled = @()
  for ($i = 0; $i -lt $MaxPoints; $i++) {
    $sampled += $Points[[int][Math]::Round($i * $step)]
  }
  return $sampled
}

function Get-YahooIntradayTrend([string]$Symbol, [string]$DateText) {
  $targetDate = [datetime]::ParseExact($DateText, 'yyyy-MM-dd', $null)
  $period1 = ConvertTo-UnixSecondsUtc $targetDate.AddDays(-1).Date
  $period2 = ConvertTo-UnixSecondsUtc $targetDate.AddDays(2).Date
  $escapedSymbol = [uri]::EscapeDataString($Symbol)
  $url = "https://query1.finance.yahoo.com/v8/finance/chart/$escapedSymbol" +
    "?period1=$period1&period2=$period2&interval=5m&includePrePost=false&events=history"

  $lastError = $null
  $payload = $null
  for ($attempt = 0; $attempt -lt 3; $attempt++) {
    try {
      $response = Invoke-WebRequest -Uri $url -UseBasicParsing -Headers @{ 'User-Agent' = 'Mozilla/5.0' }
      $payload = $response.Content | ConvertFrom-Json
      break
    } catch {
      $lastError = $_
      Start-Sleep -Seconds (1 + $attempt)
    }
  }
  if (-not $payload) {
    throw "Yahoo intraday request failed for $Symbol $DateText ($url): $($lastError.Exception.Message)"
  }
  if ($payload.chart.error) {
    throw "Yahoo intraday error for ${Symbol}: $($payload.chart.error.description)"
  }
  $result = @($payload.chart.result)[0]
  if (-not $result) {
    return $null
  }

  $timestamps = @($result.timestamp)
  $closes = @($result.indicators.quote[0].close)
  $gmtoffset = [int]$result.meta.gmtoffset
  $points = @()

  for ($i = 0; $i -lt $timestamps.Count; $i++) {
    if ($i -ge $closes.Count -or $null -eq $closes[$i]) {
      continue
    }
    $localTime = [DateTimeOffset]::FromUnixTimeSeconds([int64]$timestamps[$i]).UtcDateTime.AddSeconds($gmtoffset)
    if ($localTime.ToString('yyyy-MM-dd') -ne $DateText) {
      continue
    }
    $points += [pscustomobject]@{
      time = $localTime.ToString('HH:mm')
      value = [double]$closes[$i]
    }
  }

  if ($points.Count -eq 0) {
    return $null
  }

  return [pscustomobject]@{
    date = $DateText
    source_ids = @('yahoo_intraday_chart')
    points = @(Downsample-Points $points)
  }
}

function Has-TrendPoints($Trend) {
  return $null -ne $Trend -and $null -ne $Trend.points -and @($Trend.points).Count -gt 0
}

$etfChanged = 0
$benchmarkChanged = 0

foreach ($entry in $manifest.daily_files) {
  $dailyPath = Join-Path $DataDir $entry.file
  $daily = Get-Content -LiteralPath $dailyPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $changed = $false

  foreach ($row in @($daily.etf_records)) {
    if (Has-TrendPoints $row.trend) {
      continue
    }
    $trend = Get-YahooIntradayTrend (Get-EtfYahooSymbol $row.code) $row.trade_date
    if ($trend) {
      $row.trend = $trend
      $etfChanged += 1
      $changed = $true
    }
  }

  foreach ($row in @($daily.benchmark_records)) {
    if (Has-TrendPoints $row.trend) {
      continue
    }
    $symbol = if ($row.symbol -eq 'NDX') { '^NDX' } else { $row.symbol }
    $trend = Get-YahooIntradayTrend $symbol $row.quote_date
    if ($trend) {
      $row.trend = $trend
      $benchmarkChanged += 1
      $changed = $true
    }
  }

  if ($changed) {
    $json = $daily | ConvertTo-Json -Depth 100
    [System.IO.File]::WriteAllText((Resolve-Path -LiteralPath $dailyPath), $json, $utf8NoBom)
  }
}

$manifest.generated_at = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
$manifest.etfs = $config.etfs
$manifest.benchmarks = $config.benchmarks
$manifest.sources = $config.sources
foreach ($entry in $manifest.daily_files) {
  $dailyPath = Join-Path $DataDir $entry.file
  $daily = Get-Content -LiteralPath $dailyPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $entry.etf_count = @($daily.etf_records).Count
  $entry.benchmark_count = @($daily.benchmark_records).Count
}
$manifestJson = $manifest | ConvertTo-Json -Depth 100
[System.IO.File]::WriteAllText((Resolve-Path -LiteralPath $manifestPath), $manifestJson, $utf8NoBom)

Write-Output "refreshed $etfChanged ETF trend rows and $benchmarkChanged benchmark trend rows to $DataDir"
