from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Text,
    Boolean,
    Float,
    JSON,
    event,
)
from sqlalchemy.orm import relationship
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import UUID
from core.utils.types import GUID

from core.utils.database import Base



class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True)
    uuid = Column(
        GUID(), default=uuid4, unique=True, nullable=False, index=True
    )
    version = Column(Integer, default=1, nullable=False)
    conflict_data = Column(JSON, nullable=True)
    sync_state = Column(JSON, nullable=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    created_by = relationship("User")
    devices = relationship("Device", back_populates="site")
    memberships = relationship("SiteMembership", back_populates="site")


class SiteMembership(Base):
    __tablename__ = "site_memberships"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id"), primary_key=True)

    user = relationship("User", back_populates="site_memberships")
    site = relationship("Site", back_populates="memberships")


class ConfigBackup(Base):
    __tablename__ = "config_backups"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    config_text = Column(Text, nullable=False)
    source = Column(String, nullable=False)
    queued = Column(Boolean, default=False)
    status = Column(String, nullable=True)
    port_name = Column(String, nullable=True)

    device = relationship("Device", back_populates="backups")


class User(Base):
    """User account with role-based permissions."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    uuid = Column(
        GUID(), default=uuid4, unique=True, nullable=False, index=True
    )
    version = Column(Integer, default=1, nullable=False)
    conflict_data = Column(JSON, nullable=True)
    sync_state = Column(JSON, nullable=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="viewer")
    is_active = Column(Boolean, default=True)
    theme = Column(String, nullable=False, default="dark_colourful")
    font = Column(String, nullable=False, default="sans")
    menu_style = Column(String, nullable=False, default="tabbed")
    menu_tab_color = Column(String, nullable=True)
    menu_bg_color = Column(String, nullable=True)
    menu_stick_theme = Column(Boolean, nullable=False, default=True)
    menu_tab_colors = Column(JSON, nullable=True)
    table_grid_style = Column(String, nullable=False, default="normal")
    icon_style = Column(String, nullable=False, default="lucide")
    scroll_handoff_enabled = Column(Boolean, nullable=False, default=True)
    ssh_username = Column(String, nullable=True)
    ssh_password = Column(String, nullable=True)
    ssh_port = Column(Integer, nullable=True, default=22)
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_location_lat = Column(Float, nullable=True)
    last_location_lon = Column(Float, nullable=True)

    site_memberships = relationship("SiteMembership", back_populates="user")


class UserSSHCredential(Base):
    __tablename__ = "user_ssh_credentials"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=True)
    private_key = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    user = relationship("User")


class SystemTunable(Base):
    """Key/value settings that control system behavior."""

    __tablename__ = "system_tunables"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)
    function = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    data_type = Column(String, nullable=False, default="text")
    options = Column(String, nullable=True)
    description = Column(String, nullable=True)


class AuditLog(Base):
    """Record user actions for auditing configuration changes."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action_type = Column(String, nullable=False)
    device_id = Column(
        Integer,
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
    )
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    details = Column(Text, nullable=True)

    user = relationship("User")
    device = relationship("Device", passive_deletes=True)





class BannedIP(Base):
    __tablename__ = "banned_ips"

    id = Column(Integer, primary_key=True)
    ip_address = Column(String, unique=True, nullable=False)
    ban_reason = Column(String, nullable=False)
    banned_until = Column(DateTime(timezone=True), nullable=False)
    attempt_count = Column(Integer, default=0)


class LoginEvent(Base):
    __tablename__ = "login_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String, nullable=False)
    user_agent = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    success = Column(Boolean, default=False)
    location = Column(String, nullable=True)

    user = relationship("User")


class EmailLog(Base):
    """Record summary emails sent for site configuration changes."""

    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    date_sent = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    recipient_count = Column(Integer, nullable=False)
    success = Column(Boolean, default=True)
    details = Column(Text, nullable=True)

    site = relationship("Site")


class SNMPTrapLog(Base):
    __tablename__ = "snmp_trap_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    source_ip = Column(String, nullable=False)
    trap_oid = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)

    device = relationship("Device")
    site = relationship("Site")


class SyslogEntry(Base):
    __tablename__ = "syslog_entries"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    source_ip = Column(String, nullable=False)
    severity = Column(String, nullable=True)
    facility = Column(String, nullable=True)
    message = Column(Text, nullable=True)

    device = relationship("Device")
    site = relationship("Site")


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    name = Column(String, nullable=False)
    position = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)

    user = relationship("User")
    site = relationship("Site")


class SiteDashboardWidget(Base):
    __tablename__ = "site_dashboard_widgets"

    site_id = Column(Integer, ForeignKey("sites.id"), primary_key=True)
    name = Column(String, primary_key=True)
    position = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)

    site = relationship("Site")


class ColumnPreference(Base):
    __tablename__ = "column_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    view = Column(String, nullable=False)
    name = Column(String, nullable=False)
    position = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)

    user = relationship("User")


class TablePreference(Base):
    __tablename__ = "table_preferences"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    table_id = Column(String, primary_key=True)
    column_widths = Column(Text, nullable=True)
    visible_columns = Column(Text, nullable=True)

    user = relationship("User")


class ImportLog(Base):
    __tablename__ = "import_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    file_name = Column(String, nullable=False)
    device_count = Column(Integer, default=0)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    notes = Column(Text, nullable=True)
    success = Column(Boolean, default=True)

    user = relationship("User")
    site = relationship("Site")


class SiteKey(Base):
    """API key used by local sites to authenticate with the cloud."""

    __tablename__ = "site_keys"

    id = Column(Integer, primary_key=True)
    site_id = Column(String, unique=True, nullable=False)
    site_name = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    active = Column(Boolean, default=True)


class CustomColumn(Base):
    """Metadata for columns added at runtime."""

    __tablename__ = "custom_columns"

    id = Column(Integer, primary_key=True)
    table_name = Column(String, nullable=False)
    column_name = Column(String, nullable=False)
    data_type = Column(String, nullable=False)
    default_value = Column(String, nullable=True)
    user_visible = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class SystemMetric(Base):
    """Periodic snapshot of system metrics."""

    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    data = Column(JSON, nullable=False)


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, nullable=False)
    model_name = Column(String, nullable=False)
    action = Column(String, nullable=False)
    origin = Column(String, nullable=False)
    target = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class ConflictLog(Base):
    __tablename__ = "conflict_logs"

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, nullable=False)
    model_name = Column(String, nullable=False)
    local_version = Column(Integer, nullable=False)
    cloud_version = Column(Integer, nullable=False)
    resolved_version = Column(Integer, nullable=False)
    resolution_time = Column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )


class DuplicateResolutionLog(Base):
    __tablename__ = "duplicate_resolution_logs"

    id = Column(Integer, primary_key=True)
    model_name = Column(String, nullable=False)
    kept_id = Column(Integer, nullable=False)
    removed_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class DeletionLog(Base):
    __tablename__ = "deletion_logs"

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, nullable=False)
    model_name = Column(String, nullable=False)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    deleted_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    origin = Column(String, nullable=True)


class SyncIssue(Base):
    __tablename__ = "sync_issues"

    id = Column(Integer, primary_key=True)
    model_name = Column(String, nullable=False)
    field_name = Column(String, nullable=False)
    issue_type = Column(String, nullable=False)
    instance = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class SyncError(Base):
    __tablename__ = "sync_errors"

    id = Column(Integer, primary_key=True)
    model_name = Column(String, nullable=False)
    action = Column(String, nullable=False)
    error_trace = Column(Text, nullable=False)
    error_hash = Column(String, unique=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class BootError(Base):
    __tablename__ = "boot_errors"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    error_message = Column(String, nullable=False)
    traceback = Column(Text, nullable=False)
    instance_type = Column(String, nullable=False)


class DBError(Base):
    __tablename__ = "db_errors"

    id = Column(Integer, primary_key=True)
    model_name = Column(String, nullable=True)
    action = Column(String, nullable=True)
    error_message = Column(String, nullable=False)
    traceback = Column(Text, nullable=False)
    user = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class SchemaVersion(Base):
    __tablename__ = "schema_versions"

    id = Column(Integer, primary_key=True)
    alembic_revision_id = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    instance_type = Column(String, nullable=False)

def _update_timestamp(mapper, connection, target) -> None:
    """Refresh the updated_at field before persisting changes."""
    target.updated_at = datetime.now(timezone.utc)


_SYNC_MODELS = [
    Site,
    User,
]

for _model in _SYNC_MODELS:
    event.listen(_model, "before_update", _update_timestamp)
