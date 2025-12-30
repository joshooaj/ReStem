"""
Migration script to add demucs_command column to jobs table.
Run this once if you have an existing database.
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://demucs:demucs123@postgres:5432/demucs")

def migrate():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='jobs' AND column_name='demucs_command'
        """))
        
        if result.fetchone():
            print("✅ Column 'demucs_command' already exists")
            return
        
        # Add the column
        print("Adding 'demucs_command' column to jobs table...")
        conn.execute(text("""
            ALTER TABLE jobs 
            ADD COLUMN demucs_command TEXT
        """))
        conn.commit()
        print("✅ Migration complete!")

if __name__ == "__main__":
    migrate()
