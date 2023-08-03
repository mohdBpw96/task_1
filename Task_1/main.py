from fastapi import FastAPI, Form, UploadFile, Request
from fastapi.responses import HTMLResponse
from typing_extensions import Annotated
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer
from werkzeug.security import generate_password_hash
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pymongo import MongoClient
import base64


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory='templates')

# PostgreSQL database configuration
pg_engine = create_engine('postgresql://postgres:mohammed123@localhost:5432/xpayback_task')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
Base = declarative_base()

# MongoDB database configuration
mongo_client = MongoClient('mongodb://localhost:27017')
mongo_db = mongo_client['xpayback_task']
mongo_collection = mongo_db['profiles']


# PostgreSQL database user table model
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    phone = Column(String, unique=True)

    class Config:
        orm_mode = True 


@app.get("/register-user", response_class=HTMLResponse)
def register_user_page(request: Request):
    return templates.TemplateResponse('register_user.html', {'request': request})


@app.post("/register")
async def register_user(
        request: Request,
        full_name: Annotated[str, Form()],
        email: Annotated[str, Form()],
        password: Annotated[str, Form()],
        phone: Annotated[str, Form()],
        profile_picture: Annotated[UploadFile, Form()]
    ):

    # Check if the email already exists in PostgreSQL database
    print("Checking if the email already exists in the PostgreSQL database")

    pg_session = SessionLocal()
    user_object = pg_session.query(User).filter(User.email == email).first()
    if user_object:
        print("User already registered")
        return {"message": "User Already Registered!", "code": False}

    # Save user data to PostgreSQL
    print("Saving user data to PostgreSQL")
    new_user = User(
        full_name = full_name,
        email = email,
        password = generate_password_hash(password, method='scrypt'),
        phone = phone
    )
    pg_session.add(new_user)
    pg_session.commit()

    print("Saved to PostgreSQL DB")

    user_id = pg_session.query(User).filter(User.email == email).first().id

    # Save profile picture to MongoDB
    print("Saving profile picture to MongoDB")
    profile_data = {'user_id': user_id, "email": email, "profile_picture": profile_picture.file.read()}
    mongo_collection.insert_one(profile_data)
    print("Profile picture saved to MongoDB")


    return {"message": "User Registered Successfully!", "code": True}


@app.get("/registered-user-details", response_class=HTMLResponse)
def registered_user_details_page(request: Request, email = None):
    params = {}
    params['request'] = request

    if email is not None:
        pg_session = SessionLocal()
        user_object = pg_session.query(User).filter(User.email == email).first()
        if user_object:
            params['name'] = user_object.full_name
            params['email'] = user_object.email
            params['phone'] = user_object.phone

            profile_pic = dict(mongo_collection.find_one({'email': email}))
            params['profile_picture'] = base64.b64encode(profile_pic['profile_picture'])
            params['profile_picture'] = str(params['profile_picture']).lstrip("b'").rstrip("'")
        else:
            params['not_found_message'] = f"No registered user found having email address as '{email}'!"


    return templates.TemplateResponse('registered_user_details.html', params)

