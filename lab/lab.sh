#!/usr/bin/env bash
# Orquestra o laboratório Lateral.
#   ./lab.sh subir
#   ./lab.sh demo [cenario]          fixtures determinísticos (sem API)
#   ./lab.sh rodar <cenario>         dois agentes Haiku em paralelo + Lateral
#   ./lab.sh verificar
#   ./lab.sh descer
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"
export PYTHONPATH="$ROOT"
export LAB_PORTA="${LAB_PORTA:-3310}"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  export PATH="$ROOT/.venv/bin:$PATH"
fi
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

subir() {
  [[ -f "$ROOT/.env" ]] || { echo "Crie .env a partir de .env.exemplo"; exit 1; }
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
  python -c "from lab.bootstrap import subir; subir()"
}

rodar() {
  local cenario=${1:?cenario}
  local extra=()
  [[ "${2:-}" == "--fixture" || "${FIXTURE:-}" == "1" ]] && extra+=(--fixture)
  [[ "${INTENT:-1}" == "1" ]] && extra+=(--intent)
  python -m lab.run_round "$cenario" --subir "${extra[@]}"
}

demo() {
  FIXTURE=1 INTENT="${INTENT:-0}" rodar "${1:-c01-centavos-frete}" --fixture
}

verificar() {
  local saida=${1:-runs/manual}
  mkdir -p "$saida"
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
  python -m lateral --saida "$saida" --intent gitea \
    --url "http://127.0.0.1:${LAB_PORTA}" \
    --repository lab/loja \
    --token "$(cat .lab-token)"
}

descer() {
  python -c "from lab.bootstrap import descer; descer()"
}

cmd=${1:-}
shift || true
"$cmd" "$@"
