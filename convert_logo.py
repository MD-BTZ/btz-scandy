from cairosvg import svg2png
import os

# Pfade definieren
svg_path = 'app/static/images/scandy-logo.svg'
png_path = 'app/static/images/scandy-logo.png'

# SVG zu PNG konvertieren
svg2png(url=svg_path, write_to=png_path, output_width=32, output_height=32)

print(f'Logo wurde erfolgreich konvertiert und als {png_path} gespeichert') 