from __future__ import annotations

import argparse
from pathlib import Path
from commons.logging import configure_flow_logging


BASE_DIR = Path(__file__).resolve().parent
FLOW_DEFAULT_CONFIGS: dict[str, Path] = {
    "psg": BASE_DIR.parent / "0_declarations" / "psg.yaml",
    "xpap": BASE_DIR.parent / "0_declarations" / "xpap.yaml",
}


def _extract_flow_from_input_path(raw_input: str, known_flows: set[str]) -> str | None:
    path_parts = [part.lower() for part in Path(raw_input).parts]
    for index, segment in enumerate(path_parts):
        if segment not in known_flows:
            continue
        if index + 1 < len(path_parts) and path_parts[index + 1] in {"input", "extract", "transform"}:
            return segment
        if index > 0 and path_parts[index - 1] == "staging":
            return segment

    # Convención nueva en staging compartido: extract_<flow>_YYYY-MM-DD_HH-MM(.ext)
    stem = Path(raw_input).stem.lower()
    for flow in known_flows:
        if stem.startswith(f"extract_{flow}_"):
            return flow
    return None


def validate_flow_input_consistency(flow: str, raw_input: str | None) -> None:
    if not raw_input:
        return

    known_flows = set(FLOW_DEFAULT_CONFIGS.keys())
    path_flow = _extract_flow_from_input_path(raw_input, known_flows)
    if not path_flow:
        return

    if path_flow != flow:
        raise ValueError(
            f"El input pertenece al flow '{path_flow}' pero ejecutaste '--flow {flow}'. "
            f"Usa '--flow {path_flow}' o cambia la ruta de input."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runner unificado de pipelines transform")
    parser.add_argument(
        "input_positional",
        nargs="?",
        help="Ruta al archivo de entrada (argumento posicional opcional)",
    )
    parser.add_argument(
        "--flow",
        required=True,
        choices=sorted(FLOW_DEFAULT_CONFIGS.keys()),
        help="Flujo a ejecutar (define el pipeline y su YAML por defecto)",
    )
    parser.add_argument(
        "--config",
        required=False,
        default=None,
        help="Ruta al config.yaml del flujo (override opcional)",
    )
    parser.add_argument(
        "--input",
        required=False,
        default=None,
        help="Ruta al archivo de entrada (si se omite, usa autodiscovery del flujo)",
    )
    parser.add_argument(
        "--output",
        required=False,
        default=None,
        help="Ruta de salida (si se omite, usa la salida por defecto del flujo)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ejecuta validación y transformaciones sin escribir salida",
    )
    return parser.parse_args()


def resolve_config_path(flow: str, override_config: str | None) -> str:
    if override_config:
        return override_config

    config_path = FLOW_DEFAULT_CONFIGS.get(flow)
    if not config_path:
        available = ", ".join(sorted(FLOW_DEFAULT_CONFIGS.keys()))
        raise ValueError(f"Flujo no soportado: {flow}. Flujos válidos: {available}")

    return str(config_path)


def main() -> int:
    args = parse_args()
    configure_flow_logging(args.flow)

    config_path = resolve_config_path(args.flow, args.config)
    resolved_input = args.input or args.input_positional
    validate_flow_input_consistency(args.flow, resolved_input)

    if args.flow == "psg":
        from psg.main import execute as execute_psg

        return execute_psg(
            config_path=config_path,
            input_path=resolved_input,
            output_path=args.output,
            dry_run=args.dry_run,
        )

    if args.flow == "xpap":
        from xpap.main import execute as execute_xpap

        return execute_xpap(
            config_path=config_path,
            input_path=resolved_input,
            output_path=args.output,
            dry_run=args.dry_run,
        )

    available = ", ".join(sorted(FLOW_DEFAULT_CONFIGS.keys()))
    raise ValueError(f"Flujo no soportado: {args.flow}. Flujos válidos: {available}")


if __name__ == "__main__":
    raise SystemExit(main())
