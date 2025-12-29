"""
Migration script to add admin features to the database
Run this with: python backend/migrate_admin.py
"""
import os
from sqlalchemy import create_engine, text

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://demucs_user:demucs_pass@localhost:5432/demucs_db")

engine = create_engine(DATABASE_URL)

def run_migration():
    with engine.connect() as conn:
        print("Starting migration...")
        
        # Add is_admin column to users table
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0 NOT NULL"))
            conn.commit()
            print("✓ Added is_admin column to users table")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("- is_admin column already exists")
            else:
                print(f"✗ Error adding is_admin column: {e}")
        
        # Add active column to users table
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1 NOT NULL"))
            conn.commit()
            print("✓ Added active column to users table")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("- active column already exists")
            else:
                print(f"✗ Error adding active column: {e}")
        
        # Add archived column to jobs table
        try:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN archived INTEGER DEFAULT 0 NOT NULL"))
            conn.commit()
            print("✓ Added archived column to jobs table")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("- archived column already exists")
            else:
                print(f"✗ Error adding archived column: {e}")
        
        # Set first user as admin
        try:
            result = conn.execute(text("UPDATE users SET is_admin = 1 WHERE id = 1"))
            conn.commit()
            if result.rowcount > 0:
                print("✓ Set first user (ID=1) as admin")
            else:
                print("- No user with ID=1 found (create a user first)")
        except Exception as e:
            print(f"✗ Error setting admin user: {e}")
        
        print("\nMigration complete!")

if __name__ == "__main__":
    run_migration()
