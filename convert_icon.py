import sys
import os
from PySide6.QtGui import QGuiApplication, QPixmap, QPainter, QImage
from PySide6.QtSvg import QSvgRenderer

def convert_svg_to_ico(svg_path, ico_path):
    app = QGuiApplication(sys.argv)
    
    renderer = QSvgRenderer(svg_path)
    
    # Render to 256x256 image
    image = QImage(256, 256, QImage.Format.Format_ARGB32)
    image.fill(0x00000000)  # Transparent
    
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    
    # Save as png first, then use PIL to convert to true ICO with multiple sizes
    png_path = ico_path.replace(".ico", ".png")
    image.save(png_path)
    
    try:
        from PIL import Image
        img = Image.open(png_path)
        img.save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print(f"Successfully converted {svg_path} to {ico_path}")
    except Exception as e:
        print(f"Could not convert to multi-size ICO via PIL: {e}")
        # fallback to single size PyQt saving (might not be a valid multi-page ico, but often works as a hack)
        image.save(ico_path, "ICO")
        print("Used PyQt single-size ICO fallback.")

if __name__ == "__main__":
    base_dir = r"E:\Apps\Voky\src\mouthfull\assets"
    svg_file = os.path.join(base_dir, "logo.svg")
    ico_file = os.path.join(base_dir, "logo.ico")
    
    if os.path.exists(svg_file):
        convert_svg_to_ico(svg_file, ico_file)
    else:
        print("SVG file not found!")
