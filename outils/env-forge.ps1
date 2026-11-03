# Environnement de session pour les données de « ton IA ».
# À charger avec : . .\outils\env-forge.ps1 (depuis la racine du dépôt).
# Les données lourdes (téléchargements, caches, poids) restent hors du dépôt.

# Dossier des données : celui de la session s'il est déjà fixé, sinon D:\forge-ia-donnees.
if (-not $env:FORGE_DONNEES) {
    $env:FORGE_DONNEES = 'D:\forge-ia-donnees'
}

# Caches des outils, placés dans le dossier des données.
$env:UV_CACHE_DIR = Join-Path $env:FORGE_DONNEES 'cache\uv'
$env:HF_HOME = Join-Path $env:FORGE_DONNEES 'cache\huggingface'

# Création des dossiers qui n'existent pas encore.
foreach ($dossier in @($env:FORGE_DONNEES, $env:UV_CACHE_DIR, $env:HF_HOME)) {
    if (-not (Test-Path -LiteralPath $dossier)) {
        New-Item -ItemType Directory -Path $dossier | Out-Null
    }
}

# Place libre sur le lecteur qui porte le dossier des données.
$racine = [System.IO.Path]::GetPathRoot((Resolve-Path -LiteralPath $env:FORGE_DONNEES).ProviderPath)
$lecteur = New-Object System.IO.DriveInfo $racine
$libreGo = [math]::Round($lecteur.AvailableFreeSpace / 1GB, 1)

Write-Host ''
Write-Host 'Environnement des données de ton IA'
Write-Host ('  FORGE_DONNEES = {0}' -f $env:FORGE_DONNEES)
Write-Host ('  UV_CACHE_DIR  = {0}' -f $env:UV_CACHE_DIR)
Write-Host ('  HF_HOME       = {0}' -f $env:HF_HOME)
Write-Host ('  Place libre sur {0} : {1} Go' -f $racine, $libreGo)

if ($libreGo -lt 35) {
    Write-Warning ('Moins de 35 Go libres sur {0}. Libérer de la place avant de télécharger les données ; ne rien supprimer sans demander.' -f $racine)
}
