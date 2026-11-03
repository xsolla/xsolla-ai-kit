# Xsolla CLI setup for the Shop Builder path

Shop Builder has no other way in: every Shop Builder, catalog and LiveOps step on this
path runs through the Xsolla CLI, signed in as the user. Without the CLI, the path doesn't
fall back to a pasted API key or to a Publisher Account link for making one. Install it
and have the user sign in, then continue.

Sources: the Xsolla CLI's own install guide and distribution notes (Homebrew tap, public
CDN at `https://cdn.xsolla.net/xsolla-cli/`, `latest/version.json`, signed
`checksums.txt`).

## 1. Is it installed?

Run `xsolla --version`. "command not found", or "is not recognized" on Windows, means it
isn't. Say in one line that this path needs the Xsolla CLI and that you'll install it now,
then install it. The person's terminal asks them to allow the command; that is their OK.

## 2. Install

**macOS or Linux with Homebrew** (`brew --version` answers):

```bash
brew install xsolla/xsolla-cli/xsolla
```

**Windows** has no Homebrew, and the CLI's install scripts aren't published on the CDN
yet. Install the release archive from the CDN in PowerShell. Save these lines as
`install-xsolla.ps1` in a temporary folder and run
`powershell -NoProfile -ExecutionPolicy Bypass -File install-xsolla.ps1`. From Git Bash,
use the same command.

```powershell
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$release = Invoke-RestMethod 'https://cdn.xsolla.net/xsolla-cli/latest/version.json'
$platform = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'windows_arm64' } else { 'windows_amd64' }
$url = $release.assets.$platform
$work = Join-Path $env:TEMP 'xsolla-cli-install'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$zip = Join-Path $work (Split-Path $url -Leaf)
Invoke-WebRequest $url -OutFile $zip -UseBasicParsing
Invoke-WebRequest $release.checksums -OutFile (Join-Path $work 'checksums.txt') -UseBasicParsing
$hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
$name = Split-Path $url -Leaf
$line = Get-Content (Join-Path $work 'checksums.txt') |
    Where-Object { $_.Trim() -match "^$hash\s+\*?$([regex]::Escape($name))$" }
if (-not $line) { throw "Checksum mismatch for $name. Nothing was installed." }
$dir = Join-Path $env:LOCALAPPDATA 'xsolla'
Expand-Archive $zip -DestinationPath $dir -Force
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (($userPath -split ';') -notcontains $dir) {
    [Environment]::SetEnvironmentVariable('Path', "$userPath;$dir", 'User')
}
& (Join-Path $dir 'xsolla.exe') --version
```

A checksum mismatch stops before anything is installed: report it and don't retry with
another source. The new `Path` reaches new terminals only. In the current session, call
the CLI by its full path (`$env:LOCALAPPDATA\xsolla\xsolla.exe`), or in Git Bash run
`export PATH="$LOCALAPPDATA/xsolla:$PATH"` first. The kit's scripts call `xsolla` from
`PATH`.

**macOS or Linux without Homebrew**: download the archive for the platform
(`darwin_arm64`, `darwin_amd64`, `linux_amd64` or `linux_arm64`) listed in
`latest/version.json`, check it against the release's `checksums.txt` with
`shasum -a 256 -c checksums.txt --ignore-missing`, unpack it, and move `xsolla` to a
folder on `PATH`, such as `~/.local/bin`. Or install Homebrew first and use the command
above.

Then run `xsolla --version` and name the version in the first message.

## 3. Sign in: the user runs it

`xsolla auth login` opens a browser for the Publisher Account sign-in and waits for it.
Run from the agent's shell, it doesn't complete. Ask the user to do it in their own
terminal, in one short message:

1. Open a new terminal window: Terminal on macOS, PowerShell on Windows.
2. Run `xsolla auth login` and finish the sign-in in the browser it opens.
3. Reply "done".

Never ask for a session token, a password, or the browser's Publisher Account token.

## 4. Check the sign-in

After "done", run `xsolla auth list-account --json`. It must show an active, unexpired
Publisher account. Then continue with the remaining checks in
[nocode-shop-setup](../SKILL.md). The project key comes from the sign-in: `merchant-setup`
covers the case where a read-only catalog command still answers 401.

If a kit script later reports that its own `xsolla auth login` attempt failed or timed
out, ask the user to sign in again in their own terminal the same way, then rerun the
script as its error or report says.
