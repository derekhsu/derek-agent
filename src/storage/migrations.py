from __future__ import annotations

from sqlalchemy import create_engine, inspect, text


def upgrade_database(sync_database_url: str) -> None:
    engine = create_engine(sync_database_url)
    try:
        with engine.begin() as conn:
            inspector = inspect(conn)
            table_names = set(inspector.get_table_names())

            has_sessions = "sessions" in table_names
            has_messages = "messages" in table_names
            has_alembic = "alembic_version" in table_names

            if not has_sessions and not has_messages:
                conn.execute(
                    text(
                        """
                        CREATE TABLE sessions (
                            id VARCHAR NOT NULL PRIMARY KEY,
                            agent_id VARCHAR NOT NULL,
                            title TEXT,
                            created_at VARCHAR NOT NULL,
                            updated_at VARCHAR NOT NULL,
                            metadata TEXT
                        )
                        """
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_sessions_agent_id ON sessions (agent_id)"
                    )
                )
                conn.execute(
                    text(
                        """
                        CREATE TABLE messages (
                            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                            session_id VARCHAR NOT NULL,
                            role VARCHAR NOT NULL,
                            content TEXT NOT NULL,
                            timestamp VARCHAR NOT NULL,
                            metadata TEXT,
                            metrics TEXT,
                            FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE
                        )
                        """
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_messages_session_id ON messages (session_id)"
                    )
                )
            elif has_messages:
                message_columns = {column["name"] for column in inspector.get_columns("messages")}
                if "metrics" not in message_columns:
                    conn.execute(text("ALTER TABLE messages ADD COLUMN metrics TEXT"))
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_messages_session_id ON messages (session_id)"
                    )
                )
            if has_sessions:
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_sessions_agent_id ON sessions (agent_id)"
                    )
                )

            if not has_alembic:
                conn.execute(
                    text(
                        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                    )
                )
                conn.execute(
                    text(
                        "INSERT INTO alembic_version (version_num) VALUES ('0001_initial')"
                    )
                )
            else:
                current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
                if current != "0001_initial":
                    conn.execute(text("DELETE FROM alembic_version"))
                    conn.execute(
                        text(
                            "INSERT INTO alembic_version (version_num) VALUES ('0001_initial')"
                        )
                    )
    finally:
        engine.dispose()
