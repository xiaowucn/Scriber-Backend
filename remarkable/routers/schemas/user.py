from pydantic import BaseModel


class RosterLoginSchema(BaseModel):
    cn: str
    permission: str = "normal"
    url: str = ""
