from PIL import Image
import os
import win32ui
import win32con
import winerror

def png_to_ico(input_png_path, output_ico_path):
    # Convert the PNG image to a Windows-compatible bitmap
    img = Image.open(input_png_path)
    img = img.convert("RGBA")

    # Save the image as a temporary BMP file
    t_img = img.copy()
    temp_bmp_path = "temp.bmp"
    t_img.save(temp_bmp_path, format="BMP")

    # Create a function to sort by size
    def sort_icon_sizes(icons):
        return sorted(icons, key=lambda x: x[1] * x[2])

    # Try using save_ico directly if available in Pillow and save properly
    try:
        img.save(output_ico_path, 'ICO', sizes=[(256, 256), (48, 48), (32, 32), (16, 16)])
        print("Conversion succeeded using Pillow save_ico method.")
        return
    except Exception as e:
        print("Method with Pillow save_ico did not work:", str(e))

    print("Using complex method for conversion...")

    bmp = Image.open(temp_bmp_path)
    width, height = bmp.size

    try:
        # Create a temp file for BIG and SM resource sections
        fooDIB = win32ui.CreateDIB(width, height, bmp.tobytes())

        # Create an icon from the bitmap
        icon = win32ui.CreateIcoDir(fooDIB)
        icon.SaveToFile(output_ico_path)

    except Exception as e:
        print("Failed to process with temp BMP: ", str(e))

    finally:
        # Cleanup: remove the temporary BMP file
        if os.path.exists(temp_bmp_path):
            os.remove(temp_bmp_path)

if __name__ == "__main__":
    input_png = "resources/icon.png"
    output_ico = "resources/icon.ico"
    png_to_ico(input_png, output_ico)