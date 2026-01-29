import sys
from PIL import Image
import binascii

def check_lsb(image_path):
    try:
        img = Image.open(image_path)
        img = img.convert('RGB')
        pixels = img.load()
        width, height = img.size
        
        # Extract LSBs
        binary_data = ""
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                binary_data += str(r & 1)
                binary_data += str(g & 1)
                binary_data += str(b & 1)
                
        # Convert binary to text (try first 1000 chars)
        all_bytes = [binary_data[i: i+8] for i in range(0, len(binary_data), 8)]
        decoded_data = ""
        for byte in all_bytes[:1000]:
            try:
                decoded_data += chr(int(byte, 2))
            except:
                pass
                
        print(f"LSB First 100 chars: {decoded_data[:100]}")
        return decoded_data
    except Exception as e:
        print(f"Error in LSB: {e}")

def check_appended_data(image_path):
    with open(image_path, 'rb') as f:
        content = f.read()
        iend_index = content.find(b'IEND')
        if iend_index != -1:
            # IEND chunk has 4 bytes length, 4 bytes type, 0 data, 4 bytes CRC = 12 bytes total?
            # Actually IEND is 0 length (4 bytes), 'IEND' (4 bytes), CRC (4 bytes). Total 12 bytes.
            # But the content.find finds the start of 'IEND' type tag.
            # The chunk starts 4 bytes before 'IEND'.
            # content[iend_index-4 : iend_index+8] is the full chunk.
            
            # Let's just look after 'IEND' + 4 bytes (CRC)
            remaining = content[iend_index+4+4:]
            if len(remaining) > 0:
                print(f"Found {len(remaining)} bytes after IEND chunk!")
                print(f"Data: {remaining[:100]}")
                try:
                    print(f"As text: {remaining.decode('utf-8', errors='ignore')}")
                except:
                    pass
            else:
                print("No data after IEND chunk.")
        else:
            print("IEND chunk not found.")

def check_metadata(image_path):
    try:
        img = Image.open(image_path)
        print(f"Format: {img.format}, Mode: {img.mode}, Size: {img.size}")
        if img.info:
            print("Metadata found:")
            for k, v in img.info.items():
                print(f"  {k}: {v}")
        else:
            print("No simple metadata found in PIL info.")
    except Exception as e:
        print(f"Error reading metadata: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scan_stego.py <image_file>")
        sys.exit(1)
    
    fpath = sys.argv[1]
    print(f"Analyzing {fpath}...")
    print("-" * 20)
    check_metadata(fpath)
    print("-" * 20)
    check_appended_data(fpath)
    print("-" * 20)
    check_lsb(fpath)
