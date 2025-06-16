from .snmp_traps import router as snmp_traps_router
from .syslog import router as syslog_router

__all__ = ["snmp_traps_router", "syslog_router"]
