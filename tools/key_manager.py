import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import activation_manager
sys.path.append(str(Path(__file__).parent.parent))
from common.activation_manager import ActivationManager

def print_menu():
    """Print the main menu"""
    print("\n=== Mack-DDoS Share Key Manager ===")
    print("1. Generate new keys")
    print("2. List all keys")
    print("3. Check key status")
    print("4. Export keys to file")
    print("5. Exit")
    print("================================")

def generate_keys():
    """Generate new activation keys"""
    try:
        count = int(input("Enter number of keys to generate (default: 100): ") or "100")
        manager = ActivationManager()
        success, message = manager.generate_new_keys(count)
        print(message)
    except ValueError:
        print("Invalid number")
    except Exception as e:
        print(f"Error: {e}")

def list_keys():
    """List all keys with their status"""
    try:
        manager = ActivationManager()
        keys = manager.get_all_keys()
        
        print("\n=== Key Status ===")
        print(f"{'Key':<20} {'Status':<10} {'Created/Activated':<25} {'Expires':<25}")
        print("-" * 80)
        
        for key, data in keys.items():
            status = data['status']
            if status == 'Unused':
                date = datetime.fromisoformat(data['created_at']).strftime('%Y-%m-%d %H:%M:%S')
                expires = "N/A"
            else:
                date = datetime.fromisoformat(data['activated_at']).strftime('%Y-%m-%d %H:%M:%S')
                expires = datetime.fromisoformat(data['expires_at']).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"{key:<20} {status:<10} {date:<25} {expires:<25}")
    except Exception as e:
        print(f"Error: {e}")

def check_key():
    """Check status of a specific key"""
    try:
        key = input("Enter key to check: ").strip()
        manager = ActivationManager()
        is_valid, message = manager.verify_key(key)
        
        if is_valid:
            remaining_days = manager.get_remaining_days(key)
            print(f"\nKey Status: Valid")
            print(f"Remaining days: {remaining_days}")
        else:
            print(f"\nKey Status: {message}")
    except Exception as e:
        print(f"Error: {e}")

def export_keys():
    """Export keys to a file"""
    try:
        filename = input("Enter filename to export keys (default: keys_export.txt): ") or "keys_export.txt"
        manager = ActivationManager()
        keys = manager.get_all_keys()
        
        with open(filename, 'w') as f:
            f.write("=== Mack-DDoS Share Keys ===\n")
            f.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for key, data in keys.items():
                status = data['status']
                if status == 'Unused':
                    date = datetime.fromisoformat(data['created_at']).strftime('%Y-%m-%d %H:%M:%S')
                    expires = "N/A"
                else:
                    date = datetime.fromisoformat(data['activated_at']).strftime('%Y-%m-%d %H:%M:%S')
                    expires = datetime.fromisoformat(data['expires_at']).strftime('%Y-%m-%d %H:%M:%S')
                
                f.write(f"Key: {key}\n")
                f.write(f"Status: {status}\n")
                f.write(f"Created/Activated: {date}\n")
                f.write(f"Expires: {expires}\n")
                f.write("-" * 50 + "\n")
        
        print(f"Keys exported to {filename}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Main function"""
    while True:
        print_menu()
        choice = input("Enter your choice (1-5): ")
        
        if choice == '1':
            generate_keys()
        elif choice == '2':
            list_keys()
        elif choice == '3':
            check_key()
        elif choice == '4':
            export_keys()
        elif choice == '5':
            print("Goodbye!")
            break
        else:
            print("Invalid choice")

if __name__ == '__main__':
    main() 