from pydantic import BaseModel

class Mixin(BaseModel):
    files: list = []
    ratio: list = []