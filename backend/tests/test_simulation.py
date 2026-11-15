import pytest
from chemat.simulate import simulate


@pytest.mark.parametrize('players',[2,3,4])
@pytest.mark.parametrize('seed',[7,19])
def test_full_legal_match(seed,players):
    result=simulate(seed,players)
    assert result['commands']>0
    assert result['placements']==simulate(seed,players)['placements']
