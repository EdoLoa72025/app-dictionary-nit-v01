from backend.parser import (
    classify_row,
    parse_account_header,
    parse_third_party_header,
)


def test_third_party_header():
    identification, name = parse_third_party_header(
        "Nombre del tercero: 1234567890 JUAN DE LOS PALOTES"
    )
    assert identification == "1234567890"
    assert name == "JUAN DE LOS PALOTES"


def test_account_header():
    code, name = parse_account_header(
        "Cuenta contable: 11050501 Caja general"
    )
    assert code == "11050501"
    assert name == "Caja general"


def test_movement_row():
    row = {
        "identificacion": "1234567890",
        "comprobante": "RP-449-10",
        "fecha_elaboracion": "30/06/2025",
    }
    assert classify_row(row) == "movement"
