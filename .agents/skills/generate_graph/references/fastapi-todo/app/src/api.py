from fastapi import APIRouter

from .todos import TodoService

router = APIRouter(prefix="/todos")
service = TodoService()


@router.get("/")
def list_todos():
    return service.list_todos()


@router.post("/")
def create_todo(title: str):
    return service.create_todo(title)
