from pydantic import BaseModel
from typing import List, Optional
import code

class PerceptionOutput(BaseModel):
    objects_detected: List[str]
    timestamp: float
    camera_id: Optional[str] = None

class MemoryItem(BaseModel):
    fact: str
    importance: float
    source: Optional[str] = None

def main():
    output = PerceptionOutput(objects_detected = ["car", "tree"], timestamp = 148237.324)

    memory = [
        MemoryItem(fact = "Apple was seen in kitchen", importance=0.7, source = "Perception"),
        MemoryItem(fact = "Knife was seen in kitchen", importance=0.9)
    ]


    # code.interact(local=locals()) # for debugging

    print(f"dictionary output : \n{output.model_dump()}\n")
    print(f"json output : \n{output.model_dump_json()}\n")

    for m in memory:
        print(m.model_dump())


if __name__ == "__main__":
    main()

