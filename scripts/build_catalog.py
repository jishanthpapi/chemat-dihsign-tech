"""Normalize preserved workbook rows, applying explicit complete-rulebook corrections."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    rows = json.loads((ROOT / 'data/card-table-extracted.json').read_text(encoding='utf-8'))['Sheet1']
    tasks = []
    for row in rows[1:21]:
        name, formula = row[0].split(' — ')
        difficulty = row[1].split(' - ')[0].lower()
        apparatus = row[3].split(' + ')
        if name == 'Iron(II) oxalate':
            apparatus = ['Beaker', 'Stirring rod']
        reactants = row[2].split(' + ')
        tasks.append(dict(name=name, formula=formula, difficulty=difficulty,
                          points={'easy': 1, 'medium': 3, 'hard': 5}[difficulty],
                          copies=1 if difficulty == 'hard' else 2,
                          reactants=reactants, apparatus=apparatus,
                          fee=5 + len(reactants) + len(apparatus), source='Rulebook §22, pp22–24'))
    reactants, apparatus, actions = [], [], []
    mode = None
    for row in rows[21:]:
        if row[0] == 'Reactant':
            mode = 'reactant'
        elif row[0] == 'Apparatus Card':
            mode = 'apparatus'
        elif row[0] == 'Category':
            mode = 'action'
        elif row[0] and mode == 'reactant':
            reactants.append(dict(name=row[0], formula=row[1], copies=9 if row[0] == 'Sodium hydroxide' else row[3]))
        elif row[0] and mode == 'apparatus':
            apparatus.append(dict(name=row[0], copies=row[2]))
        elif row[0] and mode == 'action':
            actions.append(dict(name=row[1], category=row[0].split(' - ')[0].lower(), copies=row[3],
                                source='Rulebook §§13–17; authoritative effects in docs/rulebook-extracted.txt'))
    return dict(schema_version=1, authority='Complete rulebook; see docs/OPEN_DECISIONS.md',
                reactant=reactants, apparatus=apparatus, task=tasks, action=actions)


if __name__ == '__main__':
    (ROOT / 'data/catalog.json').write_text(json.dumps(build(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
