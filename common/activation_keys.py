import random
import string
import json
import os

def generate_activation_keys(count=50):
    """Generate random activation keys"""
    keys = []
    for _ in range(count):
        # Generate a key in format: XXXX-XXXX-XXXX-XXXX
        key = '-'.join([''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4)])
        keys.append(key)
    return keys

def save_keys(keys, filename='activation_keys.json'):
    """Save keys to a JSON file"""
    with open(filename, 'w') as f:
        json.dump(keys, f, indent=4)

def load_keys(filename='activation_keys.json'):
    """Load keys from JSON file"""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return []

# Generate and save keys if they don't exist
if not os.path.exists('activation_keys.json'):
    keys = generate_activation_keys()
    save_keys(keys) 