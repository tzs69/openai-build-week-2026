class TodoRepository:
    def __init__(self):
        self.todos = []

    def list_all(self):
        return self.todos

    def save(self, todo):
        self.todos.append(todo)
        return todo
