"""Compile the delivered report source with XeLaTeX, without rerunning analysis."""
import argparse
from pathlib import Path

from beyond_beta.latex import compile_tex


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    source = args.project_root.resolve() / 'reports/report/informe.tex'
    if not source.is_file():
        parser.error(f'No existe la fuente del informe: {source}')
    print(compile_tex(source))


if __name__ == '__main__':
    main()
