from alembic import context
from sqlalchemy import pool
from app.config import get_settings
from app.database import make_engine
from app.models import Base

config = context.config
target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(url=get_settings().database_url, target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = make_engine(get_settings().database_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=engine.dialect.name == "sqlite")
        with context.begin_transaction():
            context.run_migrations()
