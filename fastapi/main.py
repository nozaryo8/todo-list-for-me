import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, users, projects, tasks, comments, tags

app = FastAPI(
    title="Asana-like TODO API",
    description="A comprehensive task management API with projects, tasks, comments, and attachments",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切なオリジンを設定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターを追加
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(comments.router, prefix="/api/v1")
app.include_router(tags.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Asana-like TODO API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)