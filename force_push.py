import subprocess
import os

def run_git():
    commands = [
        ['git', 'add', '.'],
        ['git', 'commit', '-m', 'Integrated deployment for Vercel'],
        ['git', 'push', 'origin', 'main']
    ]
    
    for cmd in commands:
        try:
            print(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Success: {result.stdout}")
            else:
                print(f"Error: {result.stderr}")
        except Exception as e:
            print(f"Exception: {str(e)}")

if __name__ == "__main__":
    run_git()
