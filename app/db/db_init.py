from app.db.database import Base, engine
import app.db.models


def init():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init()
