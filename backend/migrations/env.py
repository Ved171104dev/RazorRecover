from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config,pool
from app.db import Base,DATABASE_URL
config=context.config
if config.config_file_name:fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url",DATABASE_URL.replace("%","%%"))
target_metadata=Base.metadata
def offline():
    context.configure(url=config.get_main_option("sqlalchemy.url"),target_metadata=target_metadata,literal_binds=True,compare_type=True)
    with context.begin_transaction():context.run_migrations()
def online():
    connectable=engine_from_config(config.get_section(config.config_ini_section),prefix="sqlalchemy.",poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection,target_metadata=target_metadata,compare_type=True)
        with context.begin_transaction():context.run_migrations()
offline() if context.is_offline_mode() else online()
