"""Public commands only; no local paths, tokens or host addresses."""
BASE = "https://raw.githubusercontent.com/gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench/main/"
INSTALL_COMMANDS = {
    "linux": "curl -fsSL " + BASE + "install.sh | bash",
    "windows": "irm '" + BASE + "install.ps1' | iex",
    "macos": "curl -fsSL " + BASE + "install.sh | bash",
}
