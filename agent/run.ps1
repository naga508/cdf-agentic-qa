# Run from the agent/ folder after activating .venv
param([switch]$Headed,[switch]$NoLLM,[string]$Only='')
$cmd = @('-m','demobank_qa')
if ($Headed) { $cmd += '--headed' }
if ($NoLLM) { $cmd += '--no-llm' }
if ($Only) { $cmd += @('--only',$Only) }
python @cmd
exit $LASTEXITCODE
