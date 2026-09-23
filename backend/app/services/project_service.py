from app.models.project import Project
from app.repositories.project_repository import ProjectRepository


class ProjectService:

    def __init__(self, repo: ProjectRepository):
        self.repo = repo

    def create(self, name, description, owner_id, organization_id):

        project = Project(
            name=name,
            description=description,
            owner_id=owner_id,
            organization_id=organization_id,
        )

        return self.repo.create(project)

    def list(self, owner_id):

        return self.repo.get_all(owner_id)

    def get(self, project_id):

        return self.repo.get_by_id(project_id)

    def delete(self, project):

        self.repo.delete(project)

    def update(self, project, name, description):

        if name is not None:
            project.name = name

        if description is not None:
            project.description = description

        self.repo.update()

        return project
