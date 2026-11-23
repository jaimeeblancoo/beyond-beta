"""Reject tracked credentials and private local files; preserve academic deliverables."""
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_TABLES = {
    'capm.csv', 'ff3.csv', 'comparison.csv', 'correlations.csv',
    'descriptive_eur.csv', 'descriptive_usd.csv',
}


def check_path(name):
    path = PurePosixPath(name)
    if name in {'docs/defense_guide.md', 'docs/presentation_script.md', 'docs/presentation_questions.md'}:
        return 'internal preparation document'
    if any(token in path.name.lower() for token in ('guion_', 'preguntas_', 'guia_defensa')):
        return 'internal preparation document'
    if path.parts[0] in {'private', 'onedrive', 'Beyond_Beta_Equipo'}:
        return 'private review pack'
    if name.startswith(('data/raw/', 'data/processed/')):
        return 'third-party input or processed observation series'
    if name.startswith('docs/assignment/') and name != 'docs/assignment/README.md':
        return 'teaching material'
    if name.startswith('reports/tables/') and path.name not in PUBLIC_TABLES:
        return 'unreviewed table'
    if path.suffix.lower() in {'.xlsx', '.xls', '.zip', '.pem', '.key', '.p12'}:
        return 'unreviewed workbook, archive or credential file'
    if any(part == '.env' or part.startswith('.env.') for part in path.parts):
        return 'environment file'
    if name in {
        'reports/figures/wealth_usd.png', 'reports/figures/capm_scatter_usd.png',
        'reports/presentation/figures/wealth.pdf', 'reports/presentation/figures/drawdown.pdf',
    }:
        return 'figure containing observation series'
    if name.startswith('reports/') and path.suffix in {'.json', '.ndjson'}:
        return 'local execution manifest'
    return None


def main():
    result = subprocess.run(
        ['git', 'ls-files', '-z'], cwd=ROOT, check=True, capture_output=True,
    )
    names = list(filter(None, result.stdout.decode('utf-8').split('\0')))
    failures = []
    secret_patterns = [
        re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
        re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}'),
        re.compile(rb'AKIA[0-9A-Z]{16}'),
    ]
    for name in names:
        reason = check_path(name)
        if reason:
            failures.append(f'{name}: {reason}')
        path = ROOT / name
        if path.is_file() and any(pattern.search(path.read_bytes()) for pattern in secret_patterns):
            failures.append(f'{name}: potential credential (value omitted)')
    if failures:
        print('\n'.join(failures), file=sys.stderr)
        return 1
    print(f'Academic repository boundaries passed for {len(names)} tracked files.')
    print('This check does not scan Git history or establish redistribution rights.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
