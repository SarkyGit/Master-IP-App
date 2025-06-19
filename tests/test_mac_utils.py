from core.utils.mac_utils import normalize_mac, display_mac, MAC_RE


def test_normalize_mac():
    assert normalize_mac('aa-bb-cc-dd-ee-ff') == 'AA:BB:CC:DD:EE:FF'
    assert normalize_mac('aabb.ccdd.eeff') == 'AA:BB:CC:DD:EE:FF'
    assert normalize_mac('AABBCCDDEEFF') == 'AA:BB:CC:DD:EE:FF'
    assert normalize_mac('AA:BB:CC:DD:EE:FF') == 'AA:BB:CC:DD:EE:FF'


def test_display_mac():
    assert display_mac('aa:bb:cc:dd:ee:ff') == 'AA:BB:CC:DD:EE:FF'
    assert display_mac(None) == ''


def test_mac_regex():
    assert MAC_RE.fullmatch('AA:BB:CC:DD:EE:FF')
    assert not MAC_RE.fullmatch('AA-BB-CC-DD-EE-FF')

