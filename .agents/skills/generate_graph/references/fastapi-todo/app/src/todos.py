from .db import TodoRepository


class TodoService:
    def __init__(self):
        self.repository = TodoRepository()

    def list_todos(self):
        return self.repository.list_all()

    def create_todo(self, title: str):
        todo = {"title": title, "done": False}
        return self.repository.save(todo)
