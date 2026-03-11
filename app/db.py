"""
Database connection and session management for arec-crm.

Reads DATABASE_URL from environment. Supports both Flask app context
and standalone script usage.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager

# Global engine and session factory (initialized by init_db)
engine = None
SessionLocal = None


def init_db(database_url=None, echo=False):
    """Initialize the database engine and session factory.

    Args:
        database_url: PostgreSQL connection string. If None, reads from DATABASE_URL env var.
        echo: If True, log all SQL statements (useful for debugging).

    Returns:
        The initialized engine.
    """
    global engine, SessionLocal

    if database_url is None:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError(
                'DATABASE_URL environment variable not set. '
                'Set it to a PostgreSQL connection string like: '
                'postgresql://user:pass@host:5432/dbname?sslmode=require'
            )

    # Create engine with conditional pooling parameters
    # SQLite doesn't support pool_size/max_overflow, only use for Postgres
    engine_kwargs = {'echo': echo}

    if database_url.startswith('postgresql'):
        engine_kwargs.update({
            'pool_size': 5,
            'max_overflow': 10,
            'pool_pre_ping': True,  # Verify connections before using
        })

    engine = create_engine(database_url, **engine_kwargs)

    # Create session factory
    SessionLocal = scoped_session(sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    ))

    return engine


def get_session():
    """Get a database session. Caller is responsible for closing it.

    Returns:
        A SQLAlchemy session.

    Usage:
        session = get_session()
        try:
            # do work
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    """
    if SessionLocal is None:
        raise RuntimeError('Database not initialized. Call init_db() first.')
    return SessionLocal()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations.

    Usage:
        with session_scope() as session:
            session.add(obj)
            # commit happens automatically on success
            # rollback happens automatically on exception
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_app(app):
    """Initialize database for Flask app. Call this from dashboard.py.

    Args:
        app: Flask application instance.
    """
    database_url = app.config.get('DATABASE_URL') or os.environ.get('DATABASE_URL')
    echo = app.config.get('SQLALCHEMY_ECHO', False)

    init_db(database_url=database_url, echo=echo)

    # Register teardown handler to remove sessions after each request
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if SessionLocal is not None:
            SessionLocal.remove()
