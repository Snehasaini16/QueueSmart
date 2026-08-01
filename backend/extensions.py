from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
# async_mode is left to auto-detect; eventlet is installed via requirements.txt
socketio = SocketIO(cors_allowed_origins="*")
