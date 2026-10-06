"""Run official StepManiaChartGenerator with conservative DDR doubles settings.

This script only configures and invokes the official generator. The library
performs foot assignment and arrow generation; no replacement planner is used.
"""
from __future__ import annotations

import argparse
import json
import os
from decimal import Decimal
from pathlib import Path
import re
import shutil
import subprocess


BASE = Path(__file__).resolve().parent
APP = Path('/tmp/rare-earth-groove/app')
DOTNET = Path('/tmp/rare-earth-groove/dotnet/dotnet')


def configuration(input_dir: Path, output_dir: Path, review_dir: Path, output_type: str = 'double') -> dict:
    low = {
        'ArrowWeights': {'dance-single': [25, 25, 25, 25], 'dance-double': [6, 12, 10, 22, 22, 12, 10, 6]},
        'StepTightening': {
            'LateralMinPanelDistance': 0.166667,
            'LongitudinalMinPanelDistance': -0.125,
            'DistanceTighteningEnabled': True,
            'DistanceMin': 1.0,
            'DistanceMax': 1.8,
            'SpeedTighteningEnabled': True,
            'SpeedMinTimeSeconds': 0.22,
            'SpeedMaxTimeSeconds': 0.45,
            'SpeedTighteningMinDistance': 0.0,
            'StretchTighteningEnabled': True,
            'StretchDistanceMin': 1.6,
            'StretchDistanceMax': 2.333333,
        },
        'LateralTightening': {
            'Enabled': True,
            'RelativeNPS': 1.35,
            'AbsoluteNPS': 5.5,
            'Speed': 1.8,
        },
        'Facing': {
            'MaxInwardPercentage': 0.0,
            'InwardPercentageCutoff': 0.5,
            'MaxOutwardPercentage': 0.0,
            'OutwardPercentageCutoff': 0.5,
        },
        'Transitions': {
            'Enabled': True,
            'StepsPerTransitionMin': 8,
            'StepsPerTransitionMax': 24,
            'MinimumPadWidth': 5,
            'TransitionCutoffPercentage': 0.5,
        },
    }
    medium = {
        'StepTightening': {'DistanceMin': 1.2, 'DistanceMax': 2.0},
        'Transitions': {'StepsPerTransitionMin': 12, 'StepsPerTransitionMax': 40},
    }
    heavy = {
        'StepTightening': {
            'DistanceMin': 1.4,
            'DistanceMax': 2.333333,
            'SpeedMinTimeSeconds': 0.22,
            'SpeedMaxTimeSeconds': 0.40,
        },
        'Facing': {'MaxInwardPercentage': 0.05, 'MaxOutwardPercentage': 0.05},
        'Transitions': {'StepsPerTransitionMin': 16, 'StepsPerTransitionMax': 56},
    }
    return {
        'LoggerConfig': {
            'LogLevel': 'Info', 'LogToFile': True,
            'LogDirectory': str(review_dir / 'logs'),
            'LogFlushIntervalSeconds': 0, 'LogBufferSizeBytes': 10240,
            'LogToConsole': True,
        },
        'InputDirectory': str(input_dir), 'InputNameRegex': r'.*\.(sm|ssc)$',
        'InputChartType': 'dance-single', 'DifficultyRegex': '.',
        'OutputDirectory': str(output_dir), 'OutputChartType': f'dance-{output_type}',
        'OverwriteBehavior': 'Always', 'NonChartFileCopyBehavior': 'DoNotCopy',
        'OutputVisualizations': True,
        'VisualizationsDirectory': str(review_dir / 'visualizations'),
        'ConcurrentSongCount': 1, 'RegexTimeoutSeconds': 20.0,
        'WarnOnDroppedSteps': True, 'CloseAutomaticallyWhenComplete': True,
        'DefaultExpressedChartConfig': 'NoBrackets',
        'DefaultPerformedChartConfig': 'ClassicLow',
        'ExpressedChartConfigRules': [],
        'PerformedChartConfigRules': [
            {'FileRegex': '.', 'DifficultyRegex': '^(Medium|Standard)$', 'Config': 'ClassicMedium'},
            {'FileRegex': '.', 'DifficultyRegex': '^(Hard|Heavy|Challenge|Expert)$', 'Config': 'ClassicHeavy'},
        ],
        'ExpressedChartConfigs': {
            'NoBrackets': {
                'DefaultBracketParsingMethod': 'NoBrackets',
                'BracketParsingDetermination': 'UseDefaultMethod',
            },
        },
        'PerformedChartConfigs': {'ClassicLow': low, 'ClassicMedium': medium, 'ClassicHeavy': heavy},
    }


def preserve_global_timing(source: Path, destination: Path) -> None:
    """Verify equivalent numeric timing, then retain exact source formatting."""
    original, generated = source.read_text(), destination.read_text()
    for tag in ('OFFSET', 'BPMS'):
        pattern = rf'(#{tag}:)([^;]*)(;)'
        old, new = re.search(pattern, original), re.search(pattern, generated)
        if not old or not new:
            raise ValueError(f'Missing global {tag}')
        def numbers(value: str) -> list:
            return [[Decimal(part.strip()) for part in entry.split('=')]
                    for entry in value.split(',') if entry.strip()]
        if numbers(old.group(2)) != numbers(new.group(2)):
            raise ValueError(f'Official writer changed numeric {tag}')
        generated = generated[:new.start(2)] + old.group(2) + generated[new.end(2):]
    destination.write_text(generated)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--name', required=True, help='Unique output directory under this experiment.')
    parser.add_argument('--output-type', choices=('single', 'double'), default='double')
    args = parser.parse_args()
    if '/' in args.name or args.name in ('', '.', '..'):
        parser.error('--name must be one path component')
    target = BASE / args.name
    input_dir, output_dir, review_dir = target / 'input', target / 'output', target / 'review'
    for path in (input_dir, output_dir, review_dir):
        path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.source, input_dir / args.source.name)
    config = configuration(input_dir, output_dir, review_dir, args.output_type)
    encoded = json.dumps(config, indent=2) + '\n'
    (target / 'config.json').write_text(encoded)
    (APP / 'StepManiaChartGeneratorConfig.json').write_text(encoded)
    env = dict(os.environ, DOTNET_CLI_HOME='/tmp/rare-earth-groove/dotnet-home',
               DOTNET_CLI_TELEMETRY_OPTOUT='1')
    command = [str(DOTNET), str(APP / 'StepManiaChartGenerator.dll')]
    result = subprocess.run(command, cwd=APP, env=env, text=True, capture_output=True)
    (target / 'console.log').write_text(result.stdout + result.stderr)
    print(result.stdout, end='')
    print(result.stderr, end='')
    result.check_returncode()
    destination = output_dir / args.source.name
    if not destination.exists():
        raise RuntimeError('Official generator exited without the requested output')
    preserve_global_timing(args.source, destination)
    print(f'Output: {output_dir}')


if __name__ == '__main__':
    main()
