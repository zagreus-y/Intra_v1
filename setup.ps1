# -----------------------------

# Set environment variables

# -----------------------------

$env:API_KEY = "API_KEY"
$env:CLIENT_CODE = "CLIENT_CODE"
$env:PASSWORD = "MPIN"
$env:TOTP_SECRET = "TOTP"

Write-Host "API environment variables set."

# -----------------------------

# Check if venv exists

# -----------------------------

if (Test-Path ".venv") {
Write-Host "Virtual environment already exists."


# Activate existing venv
. .\.venv\Scripts\Activate.ps1

Write-Host "Virtual environment activated."


}
else {
Write-Host "Creating virtual environment..."


# Create venv
python -m venv .venv

# Activate it
. .\.venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..."

python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Setup complete. Dependencies installed."


}
