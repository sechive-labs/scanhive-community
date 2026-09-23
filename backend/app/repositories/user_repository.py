from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str):

        return (
            self.db.query(User)
            .filter(User.email == email.lower())
            .first()
        )

    def create(self, user: User):

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def get_all(self, organization_id: int):

        return (
            self.db.query(User)
            .filter(User.organization_id == organization_id)
            .order_by(User.first_name.asc(), User.last_name.asc())
            .all()
        )

    def update(self, user: User):

        self.db.commit()
        self.db.refresh(user)

        return user
