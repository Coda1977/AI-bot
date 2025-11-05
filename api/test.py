from fastapi import FastAPI
app = FastAPI()

@app.get("/api/test")
def test():
    return {"test": "WORKING_v2.1.1", "deployment": "SUCCESS"}