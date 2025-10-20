#!/usr/bin/env python3
"""
Check available Google AI models
"""

import os
import google.generativeai as genai

# Set the API key
os.environ['GOOGLE_API_KEY'] = 'AIzaSyBErxyJLOd0zTWb5_iM2D0rNfawMpuv0fk'

try:
    # Configure Google AI
    genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
    
    print("✅ Google AI configured successfully")
    
    # List available models
    models = genai.list_models()
    print("Available models:")
    for model in models:
        print(f"  - {model.name}")
        
except Exception as e:
    print(f"❌ Google AI test failed: {e}")
    import traceback
    traceback.print_exc()
