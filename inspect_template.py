from docxtpl import DocxTemplate
import sys
import os

def get_template_variables(template_path):
    try:
        # Load the template
        doc = DocxTemplate(template_path)
        
        # Get the XML content
        xml_content = doc.get_xml()
        
        # Find all template variables (they are in the form {{ variable }})
        import re
        variables = set(re.findall(r'\{\{\s*([^\}]+)\s*\}\}', xml_content))
        
        # Filter out any formatting tags and clean up
        clean_vars = set()
        for var in variables:
            # Remove any formatting (e.g., {{ var|e }} becomes var)
            clean_var = var.split('|')[0].strip()
            clean_vars.add(clean_var)
            
        return sorted(list(clean_vars))
        
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    template_path = os.path.join('app', 'static', 'word', 'btzauftrag.docx')
    if not os.path.exists(template_path):
        print(f"Error: Template file not found at {template_path}")
        sys.exit(1)
        
    print(f"Template path: {template_path}")
    print("\nFound template variables:")
    print("-" * 40)
    
    variables = get_template_variables(template_path)
    for var in variables:
        print(f"- {var}")
