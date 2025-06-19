import os

def print_directory_structure(startpath):
    print("Projektstruktur:")
    print("===============")
    
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = '│   ' * level
        print(f'{indent}📁 {os.path.basename(root)}/')
        
        for f in files:
            if f.endswith(('.py', '.html')):
                print(f'{indent}│   📄 {f}')
                with open(os.path.join(root, f), 'r', encoding='utf-8') as file:
                    first_line = file.readline().strip()
                    print(f'{indent}│      └─ {first_line[:60]}...' if len(first_line) > 60 else f'{indent}│      └─ {first_line}')

if __name__ == "__main__":
    current_dir = os.getcwd()  # Aktuelles Verzeichnis
    print_directory_structure(current_dir)