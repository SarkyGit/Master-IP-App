import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../'))
from dotenv import load_dotenv
load_dotenv()
from alembic import context
from sqlalchemy import create_engine, text
from alembic.operations.ops import AddColumnOp
from logging.config import fileConfig
import types
import importlib.util

# Load Base without importing core package to avoid side effects
database_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'core', 'utils', 'database.py'))
db_spec = importlib.util.spec_from_file_location('core.utils.database', database_path)
database = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(database)
sys.modules['core.utils.database'] = database

# Load custom types module as part of minimal core package
types_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'core', 'utils', 'types.py'))
types_spec = importlib.util.spec_from_file_location('core.utils.types', types_path)
types_module = importlib.util.module_from_spec(types_spec)
types_spec.loader.exec_module(types_module)
sys.modules['core.utils.types'] = types_module

# Create minimal core package hierarchy
core_pkg = types.ModuleType('core')
utils_pkg = types.ModuleType('core.utils')
sys.modules['core'] = core_pkg
sys.modules['core.utils'] = utils_pkg
core_pkg.utils = utils_pkg
utils_pkg.database = database
utils_pkg.types = types_module

# Load models module explicitly
models_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'core', 'models', 'models.py'))
models_spec = importlib.util.spec_from_file_location('core.models.models', models_path)
models = importlib.util.module_from_spec(models_spec)
models_spec.loader.exec_module(models)
sys.modules['core.models.models'] = models

# Load module models so all tables are registered
inv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'modules', 'inventory', 'models.py'))
inv_spec = importlib.util.spec_from_file_location('modules.inventory.models', inv_path)
inv_models = importlib.util.module_from_spec(inv_spec)
inv_spec.loader.exec_module(inv_models)
sys.modules['modules.inventory.models'] = inv_models

net_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'modules', 'network', 'models.py'))
net_spec = importlib.util.spec_from_file_location('modules.network.models', net_path)
net_models = importlib.util.module_from_spec(net_spec)
net_spec.loader.exec_module(net_models)
sys.modules['modules.network.models'] = net_models
Base = database.Base

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def process_revision_directives(context, revision, directives):
    """Ensure NOT NULL columns have a server default when tables contain data."""
    if not getattr(config.cmd_opts, "autogenerate", False):
        return
    script = directives[0]
    conn = context.connection
    # Alembic 1.8+ removed the list_ops() helper, upgrade_ops is iterable
    # so we can access the operations via the ``ops`` attribute.
    for op in list(script.upgrade_ops.ops):
        if isinstance(op, AddColumnOp):
            column = op.column
            if not column.nullable and column.server_default is None:
                table = op.table_name
                has_data = conn.execute(text(f"SELECT 1 FROM {table} LIMIT 1")).first()
                if has_data:
                    if column.default is not None:
                        default = column.default.arg
                        if isinstance(default, bool):
                            column.server_default = text("true" if default else "false")
                        elif isinstance(default, (int, float)):
                            column.server_default = text(str(default))
                        elif isinstance(default, str):
                            column.server_default = text(f"'{default}'")
                        else:
                            pass

def run_migrations_offline():
    url = os.environ.get('DATABASE_URL')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        process_revision_directives=process_revision_directives,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = create_engine(os.environ.get('DATABASE_URL'))
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
