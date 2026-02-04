#!/usr/bin/env python3
"""
Quick fix script for portal authentication issues.
Generates bcrypt hash for admin password and displays setup instructions.
Uses bcrypt directly for compatibility.
"""
import sys
import os
from pathlib import Path

try:
    import bcrypt
except ImportError:
    print("ERROR: bcrypt not installed")
    print("Please run: pip install bcrypt")
    sys.exit(1)

def main():
    print("=" * 60)
    print("Portal Authentication Fix Script")
    print("=" * 60)
    
    # Get current .env path
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"\nERROR: .env file not found at {env_path}")
        sys.exit(1)
    
    print(f"\nFound .env file: {env_path}")
    
    # Read current .env
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    # Find current admin password
    current_password = None
    current_hash = None
    admin_email = None
    
    for line in env_content.split('\n'):
        if line.startswith('ADMIN_PASSWORD='):
            current_password = line.split('=', 1)[1].strip()
        elif line.startswith('ADMIN_PASSWORD_HASH='):
            current_hash = line.split('=', 1)[1].strip()
        elif line.startswith('ADMIN_EMAIL='):
            admin_email = line.split('=', 1)[1].strip()
    
    print(f"\nCurrent Configuration:")
    print(f"  Admin Email: {admin_email or 'NOT SET'}")
    print(f"  Admin Password (plain): {'***' if current_password else 'NOT SET'}")
    print(f"  Admin Password Hash: {'SET' if current_hash else 'EMPTY'}")
    
    if not current_password:
        print("\nERROR: ADMIN_PASSWORD not set in .env")
        print("Please set ADMIN_PASSWORD in your .env file first")
        sys.exit(1)
    
    # Generate hash using bcrypt directly
    print(f"\n{'='*60}")
    print("Generating bcrypt hash for admin password...")
    password_bytes = current_password.encode('utf-8')
    salt = bcrypt.gensalt()
    new_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    print(f"✅ Generated hash successfully!")
    print(f"\nBcrypt Hash:")
    print(f"  {new_hash}")
    
    # Ask if user wants to update .env
    print(f"\n{'='*60}")
    response = input("Do you want to update .env automatically? (y/n): ")
    
    if response.lower() == 'y':
        # Update .env
        updated_content = []
        for line in env_content.split('\n'):
            if line.startswith('ADMIN_PASSWORD_HASH='):
                updated_content.append(f'ADMIN_PASSWORD_HASH={new_hash}')
            else:
                updated_content.append(line)
        
        # Write back
        with open(env_path, 'w') as f:
            f.write('\n'.join(updated_content))
        
        print(f"\n✅ Updated .env file successfully!")
    else:
        print(f"\nTo update manually, add this to your .env file:")
        print(f"ADMIN_PASSWORD_HASH={new_hash}")
    
    # Display next steps
    print(f"\n{'='*60}")
    print("✅ ADMIN PORTAL FIX COMPLETE")
    print(f"{'='*60}")
    print("\nNext Steps:")
    print("\n1. Start the admin portal backend:")
    print("   python run_admin_portal.py")
    print("\n2. Start the admin portal frontend:")
    print("   cd admin-portal-frontend")
    print("   npm run dev")
    print("\n3. Access admin portal:")
    print("   URL: http://localhost:5500")
    print(f"   Email: {admin_email}")
    print(f"   Password: {current_password}")
    
    print(f"\n{'='*60}")
    print("DOCTOR PORTAL NOTES")
    print(f"{'='*60}")
    print("\nThe doctor portal uses Google OAuth.")
    print("To fix, verify in Google Cloud Console:")
    print("  - OAuth Client ID is enabled")
    print("  - Redirect URI is whitelisted:")
    print("    http://localhost:5000/portal/auth/oauth/google/callback")
    print("\nOR create a doctor account for email/password login:")
    print('  curl -X POST "http://localhost:5000/portal/auth/register" \\')
    print('    -H "X-API-Key: p_vhr7URkOawqX17IzrZYEIh7YnA4AaXUJluKocevYM" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"email": "doctor@example.com", "password": "test123"}\'')
    print(f"\n{'='*60}")

if __name__ == "__main__":
    main()
