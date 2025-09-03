from fastapi import APIRouter

router = APIRouter()

class Trail:
    def __init__(self, id: int, name: str, pictureUrl: str):
        self.id = id
        self.name = name
        self.pictureUrl = pictureUrl

@router.get("/trailsShowcase")
def get_trails_showcase():
    return {"trails": [Trail(1, "Trail 1", "http://example.com/trail1.jpg"), Trail(2, "Trail 2", "http://example.com/trail2.jpg")]}
