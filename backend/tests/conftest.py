import pytest

TEST_DB_URL = "postgresql://supportops:password@localhost:5436/supportops_test"


@pytest.fixture(scope="session")
def engine():
    from sqlalchemy import create_engine, text

    eng = create_engine(TEST_DB_URL, future=True)
    with eng.connect() as conn:
        conn.execute(text("SELECT 1"))
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    from sqlalchemy.orm import Session

    from backend.app import models  # noqa: F401
    from backend.app.database import Base

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture()
def client(db):
    from fastapi.testclient import TestClient

    from backend.app.database import get_db
    from backend.app.main import app

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seed(db):
    """Base mínima: 1 customer, 2 agents, 2 categorias, 3 políticas SLA."""
    from backend.app import models

    customer = models.Customer(name="Alice", email="alice@test.com")
    agents = [
        models.Agent(name="John", email="john@test.com"),
        models.Agent(name="Jane", email="jane@test.com"),
    ]
    categories = [
        models.Category(name="Network", description="Conectividade"),
        models.Category(name="Hardware", description="Dispositivos"),
    ]
    policies = [
        models.SLAPolicy(priority="High", max_resolution_time_hours=24),
        models.SLAPolicy(priority="Medium", max_resolution_time_hours=48),
        models.SLAPolicy(priority="Low", max_resolution_time_hours=72),
    ]
    db.add_all([customer, *agents, *categories, *policies])
    db.commit()

    return {
        "customer": customer,
        "agents": agents,
        "categories": categories,
        "policies": {p.priority: p for p in policies},
    }