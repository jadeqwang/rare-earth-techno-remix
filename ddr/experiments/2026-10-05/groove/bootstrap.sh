#!/usr/bin/env bash
# Reconstruct the pinned official chart generator in a user-writable directory.
set -euo pipefail
GROOVE_PATCH_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
GROOVE_WORK_ROOT=/tmp/rare-earth-groove
GROOVE_SOURCE="$GROOVE_WORK_ROOT/StepManiaChartGenerator"
mkdir -p "$GROOVE_WORK_ROOT"
if [ ! -d "$GROOVE_SOURCE/.git" ]; then
    git clone --recursive https://github.com/PerryAsleep/StepManiaChartGenerator.git "$GROOVE_SOURCE"
    git -C "$GROOVE_SOURCE" checkout d623ba935cafd036e8c002efe81a66011d8e78d3
    git -C "$GROOVE_SOURCE" submodule update --init --recursive
fi
if ! rg -q 'WriteFootworkTelemetry' "$GROOVE_SOURCE/StepManiaChartGenerator/Program.cs"; then
    git -C "$GROOVE_SOURCE" apply "$GROOVE_PATCH_DIR/generator-portability.patch"
    git -C "$GROOVE_SOURCE/StepManiaLibrary" apply "$GROOVE_PATCH_DIR/library-portability.patch"
    git -C "$GROOVE_SOURCE/StepManiaLibrary/Fumen" apply "$GROOVE_PATCH_DIR/fumen-portability.patch"
fi
if [ ! -x "$GROOVE_WORK_ROOT/dotnet/dotnet" ]; then
    curl -fL https://builds.dotnet.microsoft.com/dotnet/Sdk/10.0.100/dotnet-sdk-10.0.100-linux-x64.tar.gz -o "$GROOVE_WORK_ROOT/dotnet-sdk.tar.gz"
    python3 - "$GROOVE_WORK_ROOT/dotnet-sdk.tar.gz" <<'PY'
import hashlib
import sys
expected = 'f78dbac30c9af2230d67ff5c224de3a5dbf63f8a78d1c206594dedb80e6909d2cc8a9d865d5105c72c2fd2aa266fc0c6c77dedac60408cbccf272b116bd11b07'
with open(sys.argv[1], 'rb') as file:
    assert hashlib.file_digest(file, 'sha512').hexdigest() == expected, 'SDK checksum mismatch'
PY
    mkdir -p "$GROOVE_WORK_ROOT/dotnet"
    tar -xzf "$GROOVE_WORK_ROOT/dotnet-sdk.tar.gz" -C "$GROOVE_WORK_ROOT/dotnet"
fi
DOTNET_CLI_HOME="$GROOVE_WORK_ROOT/dotnet-home" \
NUGET_PACKAGES="$GROOVE_WORK_ROOT/nuget" \
DOTNET_CLI_TELEMETRY_OPTOUT=1 \
"$GROOVE_WORK_ROOT/dotnet/dotnet" build \
    "$GROOVE_SOURCE/StepManiaChartGenerator/StepManiaChartGenerator.csproj" \
    -c Release -o "$GROOVE_WORK_ROOT/app" -m:1 -p:BuildInParallel=false
