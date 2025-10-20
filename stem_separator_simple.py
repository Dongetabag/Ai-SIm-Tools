#!/usr/bin/env python3
"""
Simple AI Stem Separator Script
Separates audio into vocals, drums, bass, and other instruments
"""

import subprocess
import sys
import os
from pathlib import Path

def separate_audio(input_file, output_dir="output", model="htdemucs"):
    """
    Separate audio into 4 stems: vocals, drums, bass, other
    
    Args:
        input_file (str): Path to input audio file
        output_dir (str): Output directory for separated stems
        model (str): Demucs model to use
    """
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found!")
        return False
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Build command
    cmd = [
        "python3", "-m", "demucs",
        "-n", model,  # Model name
        "-o", output_dir,   # Output directory
        input_file
    ]
    
    print(f"🎵 Separating {input_file} using {model} model...")
    print(f"📁 Output will be saved to: {output_dir}")
    print("⏳ This may take a few minutes depending on file size...")
    
    try:
        # Run the separation
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Separation completed successfully!")
        
        # Show output files
        input_name = Path(input_file).stem
        model_dir = Path(output_dir) / model / input_name
        if model_dir.exists():
            print(f"\n📂 Separated stems saved to: {model_dir}")
            for stem_file in model_dir.glob("*.wav"):
                print(f"   🎶 {stem_file.name}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during separation: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ Error: Demucs not found. Please install it with: pip install demucs")
        return False

def main():
    """Main function to handle command line arguments"""
    
    if len(sys.argv) < 2:
        print("🎵 AI Stem Separator")
        print("=" * 50)
        print("Usage: python stem_separator_simple.py <audio_file> [output_dir] [model]")
        print("\nExamples:")
        print("  python stem_separator_simple.py song.mp3")
        print("  python stem_separator_simple.py song.wav output_folder")
        print("  python stem_separator_simple.py song.mp3 output_folder mdx_extra")
        print("\nAvailable models:")
        print("  htdemucs      - Recommended (fast, good quality)")
        print("  htdemucs_ft   - Fine-tuned version")
        print("  mdx_extra     - Best quality (slower)")
        print("  mdx_extra_q   - Fast processing")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    model = sys.argv[3] if len(sys.argv) > 3 else "htdemucs"
    
    # Validate model
    valid_models = ["htdemucs", "htdemucs_ft", "mdx_extra", "mdx_extra_q"]
    if model not in valid_models:
        print(f"❌ Invalid model '{model}'. Available models: {', '.join(valid_models)}")
        sys.exit(1)
    
    success = separate_audio(input_file, output_dir, model)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
