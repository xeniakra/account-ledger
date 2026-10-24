"""The requested sequence is preserved exactly, including E10 arriving after E9."""
from decimal import Decimal
from ledger import Event


def example_events() -> tuple[Event, ...]:
    return (
        Event("E1", 1, "CREDIT", "ACC-001", 1, Decimal("1200.00")),
        Event("E2", 1, "DEBIT", "ACC-001", 1, Decimal("950.00")),
        Event("E3", 2, "AUTHORIZATION", "ACC-001", 2, Decimal("200.00"), auth_id="Auth-A"),
        Event("E4", 3, "CREDIT", "ACC-001", 3, Decimal("400.00")),
        Event("E5", 4, "SETTLEMENT", "ACC-001", 4, Decimal("185.00"), auth_id="Auth-A"),
        Event("E6", 4, "SETTLEMENT", "ACC-001", 4, Decimal("180.00"), auth_id="Auth-Z"),
        Event("E7", 5, "DEBIT", "ACC-001", 2, Decimal("620.00")),
        Event("E8", 5, "AUTHORIZATION", "ACC-001", 5, Decimal("90.00"), auth_id="Auth-B"),
        Event("E9", 6, "REVERSAL", "ACC-001", 2, Decimal("620.00"), reverses="E7"),
        Event("E10", 5, "CREDIT", "ACC-002", 5, Decimal("10.000"), installments=3),
    )
