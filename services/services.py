from database.db import Get_DB
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy.exc import SQLAlchemyError


async def Get_User_By_Username(username: str, db: AsyncSession):
    print("!!FROM SERVICES!!")
    try:
        query = text("SELECT * FROM users_table WHERE username = :username")

        values = {

            "username": username
        }

        result = await db.execute(query, values)

        user = result.mappings().all()

        return user
    
    except SQLAlchemyError as e:

        print(e)

        return False
    
async def Insert_Refresh_Token(jti: str, user_id: str, expires_at:str, db: AsyncSession):
    
    try:
        query = text("INSERT INTO refresh_tokens (jti, user_id, expires_at) VALUES (:jti, :user_id, :expires_at)")

        values = {

            "jti": jti,
            "user_id": user_id,
            "expires_at": expires_at
        }

        await db.execute(query, values)

        await db.commit()

        return True

    except SQLAlchemyError as e:
        
        print(e)

        return False
    
