import pytest
from pathlib import Path

from pysnmp.smi import builder


def _load_mib_builder():
    mibBuilder = builder.MibBuilder()
    mibBuilder.loadTexts = True
    mibBuilder.add_mib_sources(
        builder.DirMibSource(
            Path(__file__).resolve().parents[2] / "pysnmp" / "smi" / "mibs"
        )
    )
    mibBuilder.load_modules("INET-ADDRESS-MIB")
    return mibBuilder


def _make_inet_address_row(mibBuilder):
    (MibTableRow, MibTableColumn) = mibBuilder.import_symbols(
        "SNMPv2-SMI", "MibTableRow", "MibTableColumn"
    )
    (InetAddressType, InetAddress) = mibBuilder.import_symbols(
        "INET-ADDRESS-MIB", "InetAddressType", "InetAddress"
    )

    inetAddressTypeColumn = MibTableColumn(
        (1, 3, 6, 1, 2, 1, 4, 34, 1, 1), InetAddressType()
    )
    inetAddressColumn = MibTableColumn((1, 3, 6, 1, 2, 1, 4, 34, 1, 2), InetAddress())
    mibBuilder.export_symbols(
        "TEST-INET-ADDRESS",
        inetAddressType=inetAddressTypeColumn,
        inetAddress=inetAddressColumn,
    )

    row = MibTableRow((1, 3, 6, 1, 2, 1, 4, 34, 1))
    row.indexNames = (
        (False, "TEST-INET-ADDRESS", "inetAddressType"),
        (False, "TEST-INET-ADDRESS", "inetAddress"),
    )
    return row


@pytest.mark.parametrize(
    "inst_id, expected_type, expected_address",
    [
        ((1, 4, 0, 0, 0, 0), "ipv4", "0.0.0.0"),
        (
            (
                2,
                16,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                1,
            ),
            "ipv6",
            "00:00:00:00:00:00:00:01",
        ),
    ],
)
def test_inetaddress_length_prefixed_index_is_parsed_correctly(
    inst_id, expected_type, expected_address
):
    mibBuilder = _load_mib_builder()
    row = _make_inet_address_row(mibBuilder)

    indices = row.getIndicesFromInstId(inst_id)

    assert indices[0].prettyPrint() == expected_type
    assert indices[1].prettyPrint() == expected_address
