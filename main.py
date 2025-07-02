import uvicorn
import os
from api.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    environment = os.environ.get("ENVIRONMENT", "development")
    
    # Production settings
    if environment == "production":
        uvicorn.run(
            "api.main:app", 
            host="0.0.0.0", 
            port=port,
            workers=4,
            worker_class="uvicorn.workers.UvicornWorker",
            access_log=True,
            log_level="info"
        )
    else:
        # Development settings
        uvicorn.run(
            "api.main:app", 
            host="0.0.0.0", 
            port=port, 
            reload=True,
            log_level="debug"
        )
