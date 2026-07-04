from PIL import Image

def main():
    png_path = r"E:\Apps\Voky\src\mouthfull\assets\logo.png"
    ico_path = r"E:\Apps\Voky\src\mouthfull\assets\logo.ico"
    try:
        img = Image.open(png_path)
        img.save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print(f"Successfully converted {png_path} to {ico_path}")
    except Exception as e:
        print(f"Error converting to ICO: {e}")

if __name__ == "__main__":
    main()
