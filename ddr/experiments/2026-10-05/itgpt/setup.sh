#!/usr/bin/env bash
# Restore this experiment's pinned official source, isolated CPU environment,
# and paper checkpoints. No original chart or release directory is modified.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
runtime_root="${1:-/tmp/rare-earth-itgpt-repro}"
source_revision="81de0bfebe02d7aba722ddcb3b417e3a94b89d7c"
model_revision="246ead2665282658b25e05c9363ea5c3e244d9c8"
archive_sha="655e8634c742635ff7e3cf8e9d205b1a08e1879ee3744514af7acab56d9e638e"
lock_sha="23ed1dcab191df155e5f6b439c4d070686fdfbbd087c8fbbb85e13e37a98ac4f"

for program in uv curl sha256sum tar; do
    command -v "$program" >/dev/null || { printf 'Required program missing: %s\n' "$program" >&2; exit 1; }
done

verify_hash() {
    local expected="$1" path="$2"
    printf '%s  %s\n' "$expected" "$path" | sha256sum --check --status
}

verify_hash "$archive_sha" "$script_dir/official-source.tar.gz"
verify_hash "$lock_sha" "$script_dir/requirements-lock.txt"

# Refuse to overwrite an unrelated working directory. This remains safe to rerun
# after a successful restore, including if a package or checkpoint download failed.
if [[ -d "$runtime_root" ]]; then
    if [[ ! -f "$runtime_root/.itgpt-source-revision" ]] ||
       [[ "$(cat "$runtime_root/.itgpt-source-revision")" != "$source_revision" ]]; then
        printf 'Choose a fresh runtime directory; existing source is not marked as this pinned restore: %s\n' "$runtime_root" >&2
        exit 1
    fi
else
    mkdir -p "$runtime_root"
    tar -xzf "$script_dir/official-source.tar.gz" --strip-components=1 -C "$runtime_root"
    printf '%s\n' "$source_revision" > "$runtime_root/.itgpt-source-revision"
fi

if [[ ! -x "$runtime_root/.venv/bin/python" ]]; then
    uv venv "$runtime_root/.venv" --python 3.13.5 --cache-dir "$runtime_root/uv-cache"
fi

# Exact pins include the CPU build suffix for torch. All named packages must
# match the checked dependency lock; no CUDA packages are requested.
uv pip sync --python "$runtime_root/.venv/bin/python" \
    --cache-dir "$runtime_root/uv-cache" \
    --index-url https://pypi.org/simple \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    --index-strategy unsafe-best-match \
    "$script_dir/requirements-lock.txt"

mkdir -p "$runtime_root/trained_models"
fetch_checkpoint() {
    local name="$1" expected="$2"
    local checkpoint="$runtime_root/trained_models/$name"
    if [[ -f "$checkpoint" ]]; then
        verify_hash "$expected" "$checkpoint" || {
            printf 'Existing checkpoint checksum mismatch: %s\n' "$checkpoint" >&2
            exit 1
        }
    else
        curl -fL --retry 3 \
            "https://huggingface.co/miguelomalley/ITGPT/resolve/$model_revision/$name" \
            -o "$checkpoint.partial"
        verify_hash "$expected" "$checkpoint.partial"
        mv -- "$checkpoint.partial" "$checkpoint"
    fi
}

fetch_checkpoint onset_paper.pt fa47f78d02e7ce72bc2e627382bfc7a30ef6ded6c94862c19d4a7b87a4f200fe
fetch_checkpoint sym_paper.pt fcb63e505994dde1079d967ca5d031f18f2bd8b06ab3e325443fb73d75f44450

ITGPT_REPO="$runtime_root" "$runtime_root/.venv/bin/python" \
    "$script_dir/load_models.py" --smoke --report "$runtime_root/restored-smoke-report.json"

printf '\nRuntime restored: %s\n' "$runtime_root"
printf 'Use Python: %s/.venv/bin/python\n' "$runtime_root"
printf 'Set ITGPT_REPO=%s when running the measured-grid adapter.\n' "$runtime_root"
