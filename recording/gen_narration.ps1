# Generates narration wav clips for the demo video using Windows' built-in
# System.Speech TTS engine (SAPI5) — fully local, free, no API key, no
# internet access required. Writes durations.json so the recording runner
# script can pace itself against exact narration lengths.

Add-Type -AssemblyName System.Speech

$here = Split-Path -Parent $MyInvocation.MyCommand.Path

$beats = [ordered]@{
    "beat1_intro"   = "Business users ask questions like, what was our revenue in electronics last month. The hard part isn't the SQL. It's knowing if you can trust the number, and where it came from."
    "beat2_normal"  = "Here's the agent answering a normal question: top five products by revenue. It writes real SQL, runs it, and explains the lineage in plain English, including flagging PII columns like email."
    "beat3_anomaly" = "Now the important part. Total revenue in electronics, May twenty twenty six. The agent scopes the SQL from the question, explains lineage again, and then flags this result against that metric's own history. A massive z score. Highly unusual. Investigate before reporting this number."
    "beat4_free"    = "No OpenAI key. No Anthropic key. Nothing paid. The SQL layer is a local template engine, DataHub itself is open source, and everything you just saw ran fully offline."
    "beat5_close"   = "Ten tests passing, covering N L to SQL, lineage, and the anomaly statistics. Thanks for watching."
}

$durations = [ordered]@{}

foreach ($name in $beats.Keys) {
    $text = $beats[$name]
    $outPath = Join-Path $here "$name.wav"

    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $synth.Rate = -1
    $synth.SetOutputToWaveFile($outPath)
    $synth.Speak($text)
    $synth.Dispose()

    $reader = New-Object System.Media.SoundPlayer
    $bytes = [System.IO.File]::ReadAllBytes($outPath)
    # WAV duration = dataSize / (sampleRate * blockAlign). Parse header directly.
    $sampleRate = [BitConverter]::ToInt32($bytes, 24)
    $blockAlign = [BitConverter]::ToInt16($bytes, 32)
    $dataSize   = [BitConverter]::ToInt32($bytes, 40)
    $durationSec = $dataSize / ($sampleRate * $blockAlign)

    $durations[$name] = [math]::Round($durationSec, 2)
    Write-Host "$name : $($durations[$name])s -> $outPath"
}

$durations | ConvertTo-Json | Out-File -Encoding utf8 (Join-Path $here "durations.json")

$total = ($durations.Values | Measure-Object -Sum).Sum
Write-Host ""
Write-Host "Total narration: $([math]::Round($total,2))s"
