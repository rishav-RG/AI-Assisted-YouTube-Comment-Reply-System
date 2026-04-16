from sqlalchemy.exc import OperationalError


_TRANSIENT_PG_CODES = {
    "08000",  # connection_exception
    "08001",  # sqlclient_unable_to_establish_sqlconnection
    "08003",  # connection_does_not_exist
    "08004",  # sqlserver_rejected_establishment_of_sqlconnection
    "08006",  # connection_failure
    "08007",  # transaction_resolution_unknown
    "08P01",  # protocol_violation
    "53300",  # too_many_connections
    "57P01",  # admin_shutdown
    "57P02",  # crash_shutdown
    "57P03",  # cannot_connect_now
}

_TRANSIENT_MARKERS = (
    "ssl syscall error: eof detected",
    "server closed the connection unexpectedly",
    "could not connect to server",
    "connection not open",
    "connection reset by peer",
    "connection refused",
    "terminating connection",
    "timeout expired",
)


def is_transient_db_operational_error(exc: OperationalError) -> bool:
    orig = getattr(exc, "orig", None)
    pgcode = getattr(orig, "pgcode", None)
    if pgcode in _TRANSIENT_PG_CODES:
        return True

    message = str(exc).lower()
    return any(marker in message for marker in _TRANSIENT_MARKERS)
